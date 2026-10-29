#!/usr/bin/env python3
"""Precompute Streamlit UI traces. Regen: python scripts/precompute_ui_data.py"""

from __future__ import annotations

from mpc_core.sim.config import default_demo_config
from mpc_core.sim.pid import PIDGains
from mpc_core.sim.playground import (
    PRESETS,
    PlaygroundParams,
    build_playground_scenario,
    limits_from_playground,
    run_options_from_playground,
    run_triple,
)
from mpc_core.sim.scenarios import SCENARIOS
from mpc_core.sim.simulate import RunOptions, run_mpc_step_log
from mpc_core.sim.ui_cache import (
    DEFAULT_STEP_HORIZON,
    named_playground_path,
    serialize_step_log,
    serialize_triple,
    step_through_path,
    write_json,
    SCORECARD_PATH,
)


def _playground_bundle(name: str, params: PlaygroundParams, *, tune_maxiter: int = 28) -> None:
    scenario = build_playground_scenario(params)
    cfg = default_demo_config()
    triple = run_triple(
        scenario,
        cfg=cfg,
        limits=limits_from_playground(params, cfg),
        options=run_options_from_playground(params),
        horizon_steps=params.mpc_horizon,
        mpc_tracking_weight=params.mpc_tracking_weight,
        plain_pid_gains=PIDGains(kp=params.pid_kp, ki=params.pid_ki, kd=params.pid_kd),
        tune_maxiter=tune_maxiter,
    )
    write_json(named_playground_path(name), serialize_triple(triple, params))
    print(f"Wrote playground/{name}.json")


def _scorecard(*, tune_maxiter: int = 30) -> None:
    cfg = default_demo_config()
    items = [(k, SCENARIOS[k], None) for k in SCENARIOS]
    items.append(
        (
            "model_mismatch",
            SCENARIOS["setpoint_tracking"],
            RunOptions(model_mismatch=True, noise_seed=42),
        )
    )
    rows = []
    for key, scenario, opt in items:
        triple = run_triple(scenario, cfg=cfg, options=opt, tune_maxiter=tune_maxiter)
        for label, run in (
            ("MPC", triple.mpc),
            ("PID", triple.pid),
            ("Optimized PID", triple.optimized_pid),
        ):
            m = run.metrics
            rows.append(
                {
                    "Scenario": key.replace("_", " ").title(),
                    "Controller": label,
                    "IAE": m.iae,
                    "Overshoot %": m.overshoot_pct,
                    "Settling [s]": m.settling_time_s,
                    "Energy [kWh]": m.energy_kwh,
                    "Violations": m.constraint_violation_steps,
                }
            )
    write_json(SCORECARD_PATH, {"rows": rows})
    print(f"Wrote {SCORECARD_PATH.name}")


def _step_through() -> None:
    cfg = default_demo_config()
    h = DEFAULT_STEP_HORIZON
    for key, scenario in SCENARIOS.items():
        log = run_mpc_step_log(scenario, cfg=cfg, horizon_steps=h, max_steps=70)
        write_json(
            step_through_path(key, h),
            serialize_step_log(log, scenario_key=key, horizon=h),
        )
        print(f"Wrote step_through/{key}_h{h}.json")


def main() -> None:
    print("Precomputing playground defaults and presets…", flush=True)
    default = PlaygroundParams()
    _playground_bundle("default", default)
    for name, fn in PRESETS.items():
        _playground_bundle(name, fn(PlaygroundParams()))
    print("Precomputing scorecard…", flush=True)
    _scorecard()
    print("Precomputing step-through logs…", flush=True)
    _step_through()
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
