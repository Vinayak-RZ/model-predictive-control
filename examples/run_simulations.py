#!/usr/bin/env python3
"""Batch MPC vs PID vs optimized PID; writes PNG figures and metrics under results/."""

from __future__ import annotations

import json
from pathlib import Path

from mpc_core.sim.config import default_demo_config
from mpc_core.sim.pid import PIDGains
from mpc_core.sim.pid_tune import tune_pid_gains
from mpc_core.sim.plotting import save_triple_figure
from mpc_core.sim.scenarios import SCENARIOS
from mpc_core.sim.simulate import RunOptions, run_closed_loop


def _metrics_dict(m) -> dict:
    return m.__dict__


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = default_demo_config()
    summary: dict[str, dict] = {}

    scenario_items = list(SCENARIOS.items()) + [
        (
            "model_mismatch",
            SCENARIOS["setpoint_tracking"],
            RunOptions(model_mismatch=True),
        )
    ]

    for item in scenario_items:
        if len(item) == 2:
            key, scenario = item
            opt = None
        else:
            key, scenario, opt = item
        options = opt or RunOptions()
        tune = tune_pid_gains(scenario, cfg=cfg, options=options, maxiter=35)
        tune_ff = tune_pid_gains(
            scenario,
            cfg=cfg,
            options=options,
            maxiter=35,
            pid_measured_feedforward=True,
        )
        mpc = run_closed_loop(scenario, "mpc", cfg=cfg, options=options)
        pid = run_closed_loop(scenario, "pid", cfg=cfg, options=options)
        opt_pid = run_closed_loop(
            scenario,
            "pid",
            cfg=cfg,
            options=options,
            pid_gains=tune.gains,
            result_label="optimized_pid",
        )
        opt_pid_ff = run_closed_loop(
            scenario,
            "pid",
            cfg=cfg,
            options=options,
            pid_gains=tune_ff.gains,
            pid_measured_feedforward=True,
            result_label="optimized_pid_feedforward",
        )
        png = out_dir / f"{key}.png"
        save_triple_figure(
            title=scenario.title if key != "model_mismatch" else "Model mismatch (setpoint tracking)",
            mpc=mpc,
            pid=pid,
            optimized_pid=opt_pid,
            optimized_pid_ff=opt_pid_ff,
            path=png,
            scenario_key=key,
        )
        summary[key] = {
            "mpc": _metrics_dict(mpc.metrics),
            "pid": _metrics_dict(pid.metrics),
            "optimized_pid": _metrics_dict(opt_pid.metrics),
            "optimized_pid_feedforward": _metrics_dict(opt_pid_ff.metrics),
            "optimized_pid_gains": {
                "kp": tune.gains.kp,
                "ki": tune.gains.ki,
                "kd": tune.gains.kd,
            },
            "optimized_pid_feedforward_gains": {
                "kp": tune_ff.gains.kp,
                "ki": tune_ff.gains.ki,
                "kd": tune_ff.gains.kd,
            },
        }
        md = out_dir / f"{key}_metrics.md"
        md.write_text(
            f"# {scenario.title}\n\n"
            f"MPC vs PID vs optimized PID vs optimized PID+FF\n\n"
            f"| Metric | MPC | PID | Opt. PID | Opt. PID+FF |\n"
            f"| --- | --- | --- | --- | --- |\n"
            + _table_row("IAE", mpc, pid, opt_pid, opt_pid_ff)
            + _table_row("Violations", mpc, pid, opt_pid, opt_pid_ff)
            + _table_row("Settling [s]", mpc, pid, opt_pid, opt_pid_ff)
            + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {png}")

    (out_dir / "metrics_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(f"Done. Figures in {out_dir}")


def _table_row(name, mpc, pid, opt_pid, opt_pid_ff):
    def fmt(m, attr):
        v = getattr(m.metrics, attr)
        return "—" if v is None else f"{v:.3g}"

    attr = (
        "iae"
        if name == "IAE"
        else "constraint_violation_steps"
        if "Viol" in name
        else "settling_time_s"
    )
    return (
        f"| {name} | {fmt(mpc, attr)} | {fmt(pid, attr)} "
        f"| {fmt(opt_pid, attr)} | {fmt(opt_pid_ff, attr)} |\n"
    )


if __name__ == "__main__":
    main()
