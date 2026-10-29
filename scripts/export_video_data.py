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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = default_demo_config()

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

    dist = SCENARIOS["disturbance_rejection"]
    triple_d = run_triple(dist, cfg=cfg, tune_maxiter=30)
    (OUT / "disturbance_race.json").write_text(
        json.dumps(
            {
                "mpc": _series(triple_d.mpc),
                "pid": _series(triple_d.pid),
                "optimized_pid": _series(triple_d.optimized_pid),
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

    log = run_mpc_step_log(setpoint, cfg=cfg, horizon_steps=20, max_steps=12)
    horizon_frames = []
    for snap in log.snapshots[10:22]:
        horizon_frames.append(
            {
                "t0": snap.time_s,
                "y_meas": snap.y_meas,
                "y_ref": snap.y_ref,
                "predicted_y": snap.predicted_y,
                "u": snap.u_applied,
            }
        )
    (OUT / "horizon_frames.json").write_text(
        json.dumps(horizon_frames, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote JSON under {OUT}")


if __name__ == "__main__":
    main()
