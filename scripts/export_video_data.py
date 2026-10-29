#!/usr/bin/env python3
"""Export simulation traces and scorecard metrics for the HyperFrames video."""

from __future__ import annotations

import json
from pathlib import Path

from mpc_core.sim.config import default_demo_config
from mpc_core.sim.playground import run_triple
from mpc_core.sim.scenarios import SCENARIOS
from mpc_core.sim.simulate import RunOptions

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "video" / "data"


def _series(run) -> dict:
    return {
        "time_s": run.time_s.tolist(),
        "y_c": run.y_c.tolist(),
        "y_ref": run.y_ref.tolist(),
        "u_kw": run.u_kw.tolist(),
        "metrics": run.metrics.__dict__,
    }


def _violation_times(run, u_min: float, u_max: float, du_max: float) -> list[float]:
    times: list[float] = []
    u = run.u_kw
    t = run.time_s
    for i in range(len(u)):
        if u[i] < u_min - 1e-9 or u[i] > u_max + 1e-9:
            times.append(float(t[i]))
        if i > 0 and abs(u[i] - u[i - 1]) > du_max + 1e-6:
            times.append(float(t[i]))
    return times


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = default_demo_config()

    power = SCENARIOS["power_constraints"]
    triple_pw = run_triple(power, cfg=cfg, tune_maxiter=30)
    lo, hi, du = power.limits_override or (0.0, 250.0, 25.0)
    (OUT / "power_limits.json").write_text(
        json.dumps(
            {
                "mpc": _series(triple_pw.mpc),
                "pid": _series(triple_pw.pid),
                "optimized_pid": _series(triple_pw.optimized_pid),
                "limits": {"u_min": lo, "u_max": hi, "du_max": du},
                "violation_times_s": {
                    "pid": _violation_times(triple_pw.pid, lo, hi, du),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    setpoint = SCENARIOS["setpoint_tracking"]
    triple_sp = run_triple(setpoint, cfg=cfg, tune_maxiter=30)
    (OUT / "setpoint_jump.json").write_text(
        json.dumps(
            {
                "mpc": _series(triple_sp.mpc),
                "pid": _series(triple_sp.pid),
                "optimized_pid": _series(triple_sp.optimized_pid),
                "limits": {"u_min": 0.0, "u_max": 250.0},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    scorecard = []
    for key in list(SCENARIOS.keys()) + ["model_mismatch"]:
        scenario = SCENARIOS["setpoint_tracking"] if key == "model_mismatch" else SCENARIOS[key]
        opt = RunOptions(model_mismatch=True) if key == "model_mismatch" else None
        triple = run_triple(scenario, cfg=cfg, options=opt, tune_maxiter=28)
        for name, run in (
            ("MPC", triple.mpc),
            ("PID", triple.pid),
            ("Optimized PID", triple.optimized_pid),
        ):
            scorecard.append(
                {
                    "scenario": key,
                    "controller": name,
                    "iae": run.metrics.iae,
                    "settling_s": run.metrics.settling_time_s,
                    "violations": run.metrics.constraint_violation_steps,
                }
            )
    (OUT / "scorecard.json").write_text(json.dumps(scorecard, indent=2), encoding="utf-8")

    from mpc_core.sim.simulate import run_mpc_step_log

    log = run_mpc_step_log(
        power,
        cfg=cfg,
        horizon_steps=power.mpc_horizon or 30,
        max_steps=200,
    )
    horizon_frames = []
    for snap in log.snapshots:
        if snap.time_s < 10 or snap.time_s > 120:
            continue
        if snap.planned_u < hi - 8:
            continue
        horizon_frames.append(
            {
                "t0": snap.time_s,
                "y_meas": snap.y_meas,
                "y_ref": snap.y_ref,
                "predicted_y": snap.predicted_y,
                "u": snap.u_applied,
                "u_max": hi,
            }
        )
        if len(horizon_frames) >= 14:
            break
    if len(horizon_frames) < 4:
        horizon_frames = [
            {
                "t0": s.time_s,
                "y_meas": s.y_meas,
                "y_ref": s.y_ref,
                "predicted_y": s.predicted_y,
                "u": s.u_applied,
                "u_max": hi,
            }
            for s in log.snapshots[20:34]
        ]
    (OUT / "horizon_frames.json").write_text(
        json.dumps(horizon_frames, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote JSON under {OUT}")


if __name__ == "__main__":
    main()
