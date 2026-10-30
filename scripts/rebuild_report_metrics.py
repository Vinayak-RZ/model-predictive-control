#!/usr/bin/env python3
"""Rebuild report metrics and simulation plots from the repo sim code.

Run from the repository root after ``pip install -e ".[dev]"``::

    python3 scripts/rebuild_report_metrics.py

Writes ``report/metrics_summary.json``, ``report/figures/<scenario>.png``,
and syncs ``results/metrics_summary.json`` plus ``results/<scenario>.png``.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, replace
from pathlib import Path

from mpc_core.sim.config import DemoConfig, default_demo_config
from mpc_core.sim.pid_tune import tune_pid_gains
from mpc_core.sim.plotting import save_triple_figure
from mpc_core.sim.scenarios import SCENARIOS, ScenarioConfig
from mpc_core.sim.simulate import RunOptions, run_closed_loop

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report"
FIG = OUT / "figures"
RESULTS = ROOT / "results"
FIG.mkdir(parents=True, exist_ok=True)
RESULTS.mkdir(parents=True, exist_ok=True)


def make_cfg() -> DemoConfig:
    """Winning knobs from sweep: Nu=1 + reference preview; N=40, Qt=50.

    Multi-move (Nu>1) with move penalty raised IAE on this heater; preview was
    the change that beat scenario-tuned PID on setpoint tracking.
    """
    cfg = default_demo_config()
    return replace(
        cfg,
        horizon_steps=40,
        control_horizon=1,
        move_weight=0.0,
        terminal_weight=50.0,
        observer_gain=1.0,
        tracking_weight=1.0,
        solver_time_limit_s=2.0,
    )


def run_mpc(scenario, cfg, options=None):
    return run_closed_loop(
        scenario,
        "mpc",
        cfg=cfg,
        options=options or RunOptions(),
        mpc_tracking_weight=cfg.tracking_weight,
        mpc_control_horizon=cfg.control_horizon,
        mpc_move_weight=cfg.move_weight,
        mpc_terminal_weight=cfg.terminal_weight,
        mpc_observer_gain=cfg.observer_gain,
        mpc_preview=True,
    )


def md(m):
    return asdict(m)


def main():
    cfg = make_cfg()
    # Also evaluate "legacy" MPC (no preview, N=25, Nu=1, Qt=0) for the change log
    legacy = replace(
        cfg,
        horizon_steps=25,
        control_horizon=1,
        terminal_weight=0.0,
        move_weight=0.0,
        observer_gain=1.0,
    )

    summary = {
        "mpc_params_retuned": {
            "horizon_steps": cfg.horizon_steps,
            "control_horizon": cfg.control_horizon,
            "terminal_weight": cfg.terminal_weight,
            "move_weight": cfg.move_weight,
            "observer_gain": cfg.observer_gain,
            "tracking_weight": cfg.tracking_weight,
            "reference_preview": True,
            "solver": "L-BFGS-B (Nu=1)",
            "plant": asdict(cfg.ibh),
            "model": {
                "a": cfg.model.a,
                "b": cfg.model.b,
                "dt_s": cfg.model.dt_s,
                "fit_id": cfg.model.fit_id,
                "residual_rms": cfg.model.residual_rms,
            },
            "limits_default_kW": [cfg.limits.low, cfg.limits.high, cfg.limits.max_step],
        },
        "mpc_params_legacy": {
            "horizon_steps": 25,
            "control_horizon": 1,
            "terminal_weight": 0.0,
            "move_weight": 0.0,
            "observer_gain": 1.0,
            "reference_preview": False,
            "note": "Matches published metrics_summary.json on the PR branch before retune.",
        },
        "scenarios": {},
    }

    # Quick legacy vs retuned on setpoint only
    sc0 = SCENARIOS["setpoint_tracking"]
    leg = run_closed_loop(
        sc0, "mpc", cfg=legacy, options=RunOptions(),
        mpc_control_horizon=1, mpc_terminal_weight=0.0, mpc_move_weight=0.0,
        mpc_observer_gain=1.0, mpc_preview=False, horizon_steps=25,
    )
    ret = run_mpc(sc0, cfg)
    summary["legacy_vs_retuned_setpoint_iae"] = {
        "legacy_no_preview": leg.metrics.iae,
        "retuned_preview_N40_Qt50": ret.metrics.iae,
    }
    print("legacy IAE", leg.metrics.iae, "retuned", ret.metrics.iae)

    items = [
        ("setpoint_tracking", SCENARIOS["setpoint_tracking"], RunOptions(), None),
        ("disturbance_rejection", SCENARIOS["disturbance_rejection"], RunOptions(), None),
        ("power_constraints", SCENARIOS["power_constraints"], RunOptions(), 45),
        ("model_mismatch", SCENARIOS["setpoint_tracking"], RunOptions(model_mismatch=True), None),
    ]

    # ambient as 5th plant scenario
    amb = ScenarioConfig(
        key="ambient_step",
        title="Ambient temperature step",
        description="Ambient rises 8 C at 70 s while tracking 115 C.",
        duration_s=200,
        t_initial_c=90.0,
        u_initial_kw=110.0,
        y_ref_fn=SCENARIOS["disturbance_rejection"].y_ref_fn,
        disturbance_at_s=70.0,
        disturbance_event="ambient_step",
        pid_gains=(3.2, 0.05, 0.5),
    )
    items.append(("ambient_step", amb, RunOptions(), None))

    opt_gains = {}
    for key, scenario, options, h_override in items:
        print(f"=== {key} ===", flush=True)
        t0 = time.perf_counter()
        tune = tune_pid_gains(scenario, cfg=cfg, options=options, maxiter=35)
        opt_gains[key] = tune.gains
        kw = {}
        if h_override:
            # power scenario: keep longer prediction
            mpc = run_closed_loop(
                scenario, "mpc", cfg=cfg, options=options,
                horizon_steps=h_override,
                mpc_tracking_weight=cfg.tracking_weight,
                mpc_control_horizon=cfg.control_horizon,
                mpc_move_weight=cfg.move_weight,
                mpc_terminal_weight=cfg.terminal_weight,
                mpc_observer_gain=cfg.observer_gain,
                mpc_preview=True,
            )
        else:
            mpc = run_mpc(scenario, cfg, options=options)
        pid = run_closed_loop(scenario, "pid", cfg=cfg, options=options)
        opt_pid = run_closed_loop(
            scenario, "pid", cfg=cfg, options=options,
            pid_gains=tune.gains, result_label="optimized_pid",
        )
        title = scenario.title if key != "model_mismatch" else "Model mismatch (setpoint tracking)"
        save_triple_figure(
            title=title, mpc=mpc, pid=pid, optimized_pid=opt_pid,
            path=FIG / f"{key}.png",
        )
        if key in ("setpoint_tracking", "disturbance_rejection", "power_constraints", "model_mismatch"):
            save_triple_figure(
                title=title, mpc=mpc, pid=pid, optimized_pid=opt_pid,
                path=RESULTS / f"{key}.png",
            )
        summary["scenarios"][key] = {
            "mpc": md(mpc.metrics),
            "pid": md(pid.metrics),
            "optimized_pid": md(opt_pid.metrics),
            "optimized_pid_gains": {
                "kp": tune.gains.kp, "ki": tune.gains.ki, "kd": tune.gains.kd,
            },
            "runtime_s": time.perf_counter() - t0,
        }
        s = summary["scenarios"][key]
        print(
            f"  IAE {s['mpc']['iae']:.1f}/{s['pid']['iae']:.1f}/{s['optimized_pid']['iae']:.1f} "
            f"viol {s['mpc']['constraint_violation_steps']}/"
            f"{s['pid']['constraint_violation_steps']}/"
            f"{s['optimized_pid']['constraint_violation_steps']} "
            f"E {s['mpc']['energy_kwh']:.3f}/{s['pid']['energy_kwh']:.3f}/"
            f"{s['optimized_pid']['energy_kwh']:.3f}",
            flush=True,
        )

    # Robustness: nominal-tuned opt PID on mismatched plant
    print("=== robustness ===", flush=True)
    gains = opt_gains["setpoint_tracking"]
    mm = RunOptions(model_mismatch=True)
    mpc_mm = run_mpc(SCENARIOS["setpoint_tracking"], cfg, options=mm)
    pid_mm = run_closed_loop(SCENARIOS["setpoint_tracking"], "pid", cfg=cfg, options=mm)
    opt_mm = run_closed_loop(
        SCENARIOS["setpoint_tracking"], "pid", cfg=cfg, options=mm,
        pid_gains=gains, result_label="optimized_pid_nominal_gains",
    )
    opt_oracle = run_closed_loop(
        SCENARIOS["setpoint_tracking"], "pid", cfg=cfg, options=mm,
        pid_gains=opt_gains["model_mismatch"],
        result_label="optimized_pid_retuned_on_mismatch",
    )
    save_triple_figure(
        title="Robustness: opt. PID gains from nominal under mismatch",
        mpc=mpc_mm, pid=pid_mm, optimized_pid=opt_mm,
        path=FIG / "robustness_nominal_gains_on_mismatch.png",
    )
    summary["scenarios"]["robustness_nominal_gains_on_mismatch"] = {
        "mpc": md(mpc_mm.metrics),
        "pid": md(pid_mm.metrics),
        "optimized_pid_nominal_gains": md(opt_mm.metrics),
        "optimized_pid_retuned_on_mismatch": md(opt_oracle.metrics),
        "nominal_gains_used": {
            "kp": gains.kp, "ki": gains.ki, "kd": gains.kd,
        },
        "note": (
            "optimized_pid_nominal_gains uses gains tuned on the nominal plant; "
            "optimized_pid_retuned_on_mismatch saw the mismatched plant during tuning."
        ),
    }
    r = summary["scenarios"]["robustness_nominal_gains_on_mismatch"]
    print(
        f"  IAE mpc/pid/opt(nom)/opt(oracle) = "
        f"{r['mpc']['iae']:.1f}/{r['pid']['iae']:.1f}/"
        f"{r['optimized_pid_nominal_gains']['iae']:.1f}/"
        f"{r['optimized_pid_retuned_on_mismatch']['iae']:.1f}",
        flush=True,
    )

    text = json.dumps(summary, indent=2) + "\n"
    (OUT / "metrics_summary.json").write_text(text)
    # README table source: scenario metrics only (legacy shape)
    slim = {
        k: v
        for k, v in summary["scenarios"].items()
        if k
        in (
            "setpoint_tracking",
            "disturbance_rejection",
            "power_constraints",
            "model_mismatch",
            "ambient_step",
        )
    }
    (RESULTS / "metrics_summary.json").write_text(json.dumps(slim, indent=2) + "\n")
    print("Wrote", OUT / "metrics_summary.json")
    print("Wrote", RESULTS / "metrics_summary.json")


if __name__ == "__main__":
    main()
