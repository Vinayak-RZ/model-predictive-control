"""Optimise PID gains on the same plant, noise, and limits as closed-loop runs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from mpc_core.sim.config import DemoConfig, default_demo_config
from mpc_core.sim.pid import PIDGains
from mpc_core.sim.scenarios import ScenarioConfig
from mpc_core.sim.simulate import RunOptions, run_closed_loop
from mpc_core.thresholds import SetpointLimits


@dataclass(frozen=True)
class TuneResult:
    gains: PIDGains
    final_objective: float
    metrics_iae: float
    violation_steps: int


def _objective_from_metrics(iae: float, violation_steps: int, *, violation_weight: float) -> float:
    return iae + violation_weight * float(violation_steps)


def tune_pid_gains(
    scenario: ScenarioConfig,
    *,
    cfg: DemoConfig | None = None,
    limits: SetpointLimits | None = None,
    options: RunOptions | None = None,
    x0: tuple[float, float, float] | None = None,
    violation_weight: float = 250.0,
    maxiter: int = 40,
) -> TuneResult:
    """Minimise IAE plus a penalty on actuator constraint violations."""
    cfg = cfg or default_demo_config()
    base = options or RunOptions()
    start = x0 or scenario.pid_gains

    def objective(x: np.ndarray) -> float:
        gains = PIDGains(kp=float(x[0]), ki=float(x[1]), kd=float(x[2]))
        run = run_closed_loop(
            scenario,
            "pid",
            cfg=cfg,
            limits=limits,
            options=base,
            pid_gains=gains,
        )
        return _objective_from_metrics(
            run.metrics.iae,
            run.metrics.constraint_violation_steps,
            violation_weight=violation_weight,
        )

    bounds = [(0.05, 12.0), (0.0, 0.35), (0.0, 8.0)]
    res = minimize(
        objective,
        np.array(start, dtype=float),
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": maxiter},
    )
    best = PIDGains(kp=float(res.x[0]), ki=float(res.x[1]), kd=float(res.x[2]))
    verify = run_closed_loop(
        scenario,
        "pid",
        cfg=cfg,
        limits=limits,
        options=base,
        pid_gains=best,
    )
    obj = _objective_from_metrics(
        verify.metrics.iae,
        verify.metrics.constraint_violation_steps,
        violation_weight=violation_weight,
    )
    return TuneResult(
        gains=best,
        final_objective=float(obj),
        metrics_iae=verify.metrics.iae,
        violation_steps=verify.metrics.constraint_violation_steps,
    )
