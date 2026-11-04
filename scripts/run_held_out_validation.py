#!/usr/bin/env python3
"""Held-out IAE statistics: noise seeds, unseen scenarios, plant scale sweeps.

MPC knobs stay fixed (same as rebuild_report_metrics). Optimised PID gains are
tuned once per primary scenario at noise seed 42, then frozen for the noise
sweep. Unseen scenario variants get a fresh optimiser run per controller class.

Writes ``report/held_out_validation.json`` and ``results/held_out_validation.json``.
"""
from __future__ import annotations

import json
import statistics
from dataclasses import asdict
from pathlib import Path

import numpy as np

from mpc_core.sim.config import DemoConfig, default_demo_config
from mpc_core.sim.pid import PIDGains
from mpc_core.sim.pid_tune import tune_pid_gains
from mpc_core.sim.scenarios import SCENARIOS, ScenarioConfig
from mpc_core.sim.simulate import RunOptions, run_closed_loop
from dataclasses import replace

ROOT = Path(__file__).resolve().parents[1]


def make_cfg() -> DemoConfig:
    cfg = default_demo_config()
    return replace(
        cfg,
        horizon_steps=40,
        control_horizon=1,
        move_weight=0.0,
        terminal_weight=50.0,
        observer_gain=cfg.observer_gain,
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
OUT_REPORT = ROOT / "report" / "held_out_validation.json"
OUT_RESULTS = ROOT / "results" / "held_out_validation.json"

CONTROLLERS = ("mpc", "pid", "optimized_pid", "optimized_pid_feedforward")


def _run_all(
    scenario: ScenarioConfig,
    cfg: DemoConfig,
    options: RunOptions,
    *,
    opt_gains,
    opt_ff_gains,
    h_override: int | None = None,
) -> dict[str, float]:
    kw_mpc = dict(
        cfg=cfg,
        options=options,
        mpc_tracking_weight=cfg.tracking_weight,
        mpc_control_horizon=cfg.control_horizon,
        mpc_move_weight=cfg.move_weight,
        mpc_terminal_weight=cfg.terminal_weight,
        mpc_observer_gain=cfg.observer_gain,
        mpc_preview=True,
    )
    if h_override:
        mpc = run_closed_loop(scenario, "mpc", horizon_steps=h_override, **kw_mpc)
    else:
        mpc = run_mpc(scenario, cfg, options=options)
    pid = run_closed_loop(scenario, "pid", cfg=cfg, options=options)
    opt = run_closed_loop(
        scenario,
        "pid",
        cfg=cfg,
        options=options,
        pid_gains=opt_gains,
        result_label="optimized_pid",
    )
    opt_ff = run_closed_loop(
        scenario,
        "pid",
        cfg=cfg,
        options=options,
        pid_gains=opt_ff_gains,
        pid_measured_feedforward=True,
        result_label="optimized_pid_feedforward",
    )
    return {
        "mpc": mpc.metrics.iae,
        "pid": pid.metrics.iae,
        "optimized_pid": opt.metrics.iae,
        "optimized_pid_feedforward": opt_ff.metrics.iae,
    }


def _summarize(rows: list[dict[str, float]]) -> dict:
    out: dict = {}
    for key in CONTROLLERS:
        vals = [r[key] for r in rows]
        out[key] = {
            "mean_iae": statistics.mean(vals),
            "std_iae": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
            "n": len(vals),
        }
    wins = {k: 0 for k in CONTROLLERS}
    for r in rows:
        best = min(CONTROLLERS, key=lambda k: r[k])
        wins[best] += 1
    out["win_rate"] = {k: wins[k] / len(rows) for k in CONTROLLERS}
    out["mpc_beats_all_fraction"] = sum(
        1 for r in rows if r["mpc"] < min(r["optimized_pid"], r["optimized_pid_feedforward"])
    ) / len(rows)
    return out


def _held_out_scenarios() -> dict[str, ScenarioConfig]:
    def ref_step(low: float, high: float, t_step: float):
        def fn(time_s: np.ndarray) -> np.ndarray:
            ref = np.full_like(time_s, low, dtype=float)
            ref[time_s >= t_step] = high
            return ref

        return fn

    return {
        "setpoint_early_small": ScenarioConfig(
            key="setpoint_early_small",
            title="Held-out setpoint 75→110 at 20 s",
            description="Unseen step size and timing.",
            duration_s=180,
            t_initial_c=75.0,
            u_initial_kw=90.0,
            y_ref_fn=ref_step(75.0, 110.0, 20.0),
        ),
        "setpoint_late_large": ScenarioConfig(
            key="setpoint_late_large",
            title="Held-out setpoint 85→125 at 45 s",
            description="Unseen step size and timing.",
            duration_s=200,
            t_initial_c=85.0,
            u_initial_kw=100.0,
            y_ref_fn=ref_step(85.0, 125.0, 45.0),
        ),
        "disturbance_late": ScenarioConfig(
            key="disturbance_late",
            title="Held-out heat-loss bump at 85 s",
            description="Same profile as batch disturbance but later event.",
            duration_s=200,
            t_initial_c=90.0,
            u_initial_kw=110.0,
            y_ref_fn=SCENARIOS["disturbance_rejection"].y_ref_fn,
            disturbance_at_s=85.0,
            disturbance_event="heat_loss_bump",
            pid_gains=(3.2, 0.05, 0.5),
        ),
    }


def main() -> None:
    cfg = make_cfg()
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
    primary = [
        ("setpoint_tracking", SCENARIOS["setpoint_tracking"], RunOptions(), None),
        ("disturbance_rejection", SCENARIOS["disturbance_rejection"], RunOptions(), None),
        ("power_constraints", SCENARIOS["power_constraints"], RunOptions(), 45),
        ("model_mismatch", SCENARIOS["setpoint_tracking"], RunOptions(model_mismatch=True), None),
        ("ambient_step", amb, RunOptions(), None),
    ]

    tuned: dict[str, dict] = {}
    for key, scenario, options, _ in primary:
        tune = tune_pid_gains(scenario, cfg=cfg, options=options, maxiter=35)
        tune_ff = tune_pid_gains(
            scenario,
            cfg=cfg,
            options=options,
            maxiter=35,
            pid_measured_feedforward=True,
        )
        tuned[key] = {
            "optimized_pid": asdict(tune.gains),
            "optimized_pid_feedforward": asdict(tune_ff.gains),
        }

    report: dict = {
        "note": (
            "MPC parameters fixed from make_cfg(). Primary-scenario optimised gains "
            "tuned at noise_seed=42. Held-out checks test generalisation, not retuning MPC."
        ),
        "noise_seed_sweep": {"seeds": list(range(20)), "by_scenario": {}},
        "unseen_scenarios": {},
        "plant_scale_sweep": {},
    }

    # 20 noise seeds on primary scenarios (frozen opt gains)
    for key, scenario, base_opt, h_override in primary:
        rows = []
        opt_g = tuned[key]["optimized_pid"]
        opt_ff_g = tuned[key]["optimized_pid_feedforward"]

        for seed in range(20):
            options = RunOptions(
                noise_seed=seed,
                noise_std_c=0.15 if seed % 2 == 0 else 0.0,
            )
            if key == "model_mismatch":
                options = RunOptions(
                    noise_seed=seed,
                    noise_std_c=0.15 if seed % 2 == 0 else 0.0,
                    model_mismatch=True,
                )
            iae = _run_all(
                scenario,
                cfg,
                options,
                opt_gains=PIDGains(**opt_g),
                opt_ff_gains=PIDGains(**opt_ff_g),
                h_override=h_override,
            )
            rows.append(iae)
        report["noise_seed_sweep"]["by_scenario"][key] = _summarize(rows)

    # Unseen scenario variants (retune opt / opt+ff on each variant)
    for vkey, scenario in _held_out_scenarios().items():
        options = RunOptions()
        tune = tune_pid_gains(scenario, cfg=cfg, options=options, maxiter=35)
        tune_ff = tune_pid_gains(
            scenario,
            cfg=cfg,
            options=options,
            maxiter=35,
            pid_measured_feedforward=True,
        )
        iae = _run_all(
            scenario,
            cfg,
            options,
            opt_gains=tune.gains,
            opt_ff_gains=tune_ff.gains,
        )
        report["unseen_scenarios"][vkey] = {
            "iae": iae,
            "optimized_pid_gains": asdict(tune.gains),
            "optimized_pid_feedforward_gains": asdict(tune_ff.gains),
        }

    # +/-20% plant parameter scales on setpoint tracking
    scales = [
        ("mass_0p8", dict(plant_mass_scale=0.8)),
        ("mass_1p2", dict(plant_mass_scale=1.2)),
        ("eta_0p8", dict(plant_eta_scale=0.8)),
        ("eta_1p2", dict(plant_eta_scale=1.2)),
        ("U_0p8", dict(plant_u_scale=0.8)),
        ("U_1p2", dict(plant_u_scale=1.2)),
    ]
    scenario = SCENARIOS["setpoint_tracking"]
    opt_g = PIDGains(**tuned["setpoint_tracking"]["optimized_pid"])
    opt_ff_g = PIDGains(**tuned["setpoint_tracking"]["optimized_pid_feedforward"])
    scale_rows = []
    for label, kwargs in scales:
        options = RunOptions(**kwargs)
        iae = _run_all(
            scenario,
            cfg,
            options,
            opt_gains=opt_g,
            opt_ff_gains=opt_ff_g,
        )
        scale_rows.append({"label": label, **iae})
    report["plant_scale_sweep"] = {
        "scenario": "setpoint_tracking",
        "frozen_gains_from_nominal_tune": True,
        "runs": scale_rows,
        "summary": _summarize([{k: r[k] for k in CONTROLLERS} for r in scale_rows]),
    }

    # Aggregate noise sweep (5 scenarios × 20 seeds)
    agg_rows = []
    for key, scenario, _, h_override in primary:
        opt_g = PIDGains(**tuned[key]["optimized_pid"])
        opt_ff_g = PIDGains(**tuned[key]["optimized_pid_feedforward"])
        for seed in range(20):
            options = RunOptions(
                noise_seed=seed,
                noise_std_c=0.15 if seed % 2 == 0 else 0.0,
            )
            if key == "model_mismatch":
                options = RunOptions(
                    noise_seed=seed,
                    noise_std_c=0.15 if seed % 2 == 0 else 0.0,
                    model_mismatch=True,
                )
            agg_rows.append(
                _run_all(
                    scenario,
                    cfg,
                    options,
                    opt_gains=opt_g,
                    opt_ff_gains=opt_ff_g,
                    h_override=h_override,
                )
            )
    report["noise_seed_sweep"]["aggregate"] = _summarize(agg_rows)

    text = json.dumps(report, indent=2) + "\n"
    OUT_REPORT.write_text(text)
    OUT_RESULTS.write_text(text)
    print("Wrote", OUT_REPORT)
    agg = report["noise_seed_sweep"]["aggregate"]
    print(
        "Noise aggregate win rates:",
        {k: f"{agg['win_rate'][k]:.2%}" for k in CONTROLLERS},
    )
    print("MPC beats both opt PID variants:", f"{agg['mpc_beats_all_fraction']:.2%}")


if __name__ == "__main__":
    main()
