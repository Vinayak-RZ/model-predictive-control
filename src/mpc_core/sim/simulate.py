"""Run MPC or PID against the heater plant for one scenario."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from mpc_core import MpcState, SetpointLimits, solve
from mpc_core.sim.config import DemoConfig, default_demo_config
from mpc_core.sim.metrics import SimulationMetrics, compute_metrics
from mpc_core.sim.pid import PIDGains, PIDState, pid_step
from mpc_core.sim.plant import IBHPlantState, apply_disturbance_event, step_plant
from mpc_core.sim.scenarios import ScenarioConfig

ControllerKind = Literal["mpc", "pid"]


@dataclass(frozen=True)
class SimulationResult:
    controller: ControllerKind
    time_s: np.ndarray
    y_c: np.ndarray
    y_ref: np.ndarray
    u_kw: np.ndarray
    d_hat: np.ndarray | None
    metrics: SimulationMetrics
    active_constraints_last: list[str]


def _reference_trace(scenario: ScenarioConfig, n_steps: int, dt_s: float) -> np.ndarray:
    time_s = np.arange(n_steps, dtype=float) * dt_s
    return scenario.y_ref_fn(time_s)


def run_closed_loop(
    scenario: ScenarioConfig,
    controller: ControllerKind,
    cfg: DemoConfig | None = None,
    *,
    horizon_steps: int | None = None,
    limits: SetpointLimits | None = None,
) -> SimulationResult:
    cfg = cfg or default_demo_config()
    dt_s = cfg.dt_s
    n_steps = int(scenario.duration_s / dt_s)
    time_s = np.arange(n_steps, dtype=float) * dt_s
    y_ref = _reference_trace(scenario, n_steps, dt_s)

    if limits is None:
        if scenario.limits_override:
            lo, hi, dmax = scenario.limits_override
            limits = SetpointLimits(cfg.limits.setpoint_id, cfg.limits.unit, lo, hi, dmax)
        else:
            limits = cfg.limits

    plant = IBHPlantState(T_c=scenario.t_initial_c, params=cfg.ibh)
    u = scenario.u_initial_kw
    mpc_state = MpcState()
    pid_state = PIDState()
    kp, ki, kd = scenario.pid_gains
    pid_gains = PIDGains(kp=kp, ki=ki, kd=kd)
    h = horizon_steps if horizon_steps is not None else (
        scenario.mpc_horizon if scenario.mpc_horizon else cfg.horizon_steps
    )

    y_hist: list[float] = []
    u_hist: list[float] = []
    d_hist: list[float | None] = []
    active_last: list[str] = []

    for k in range(n_steps):
        t = time_s[k]
        y_meas = plant.T_c
        y_r = float(y_ref[k])

        if (
            scenario.disturbance_at_s is not None
            and scenario.disturbance_event
            and t >= scenario.disturbance_at_s
        ):
            plant = apply_disturbance_event(plant, scenario.disturbance_event)

        if controller == "mpc":
            result = solve(
                cfg.model,
                [limits],
                {limits.setpoint_id: u},
                y_meas=y_meas,
                y_ref=y_r,
                horizon_steps=h,
                time_limit_s=cfg.solver_time_limit_s,
                state=mpc_state,
            )
            u = result.best[limits.setpoint_id]
            mpc_state = result.state
            active_last = list(result.active_constraints)
            d_hist.append(result.d_hat)
        else:
            du_lim = limits.max_step if scenario.pid_enforce_rate_limit else None
            u, pid_state = pid_step(
                y=y_meas,
                y_ref=y_r,
                u_prev=u,
                dt_s=dt_s,
                gains=pid_gains,
                state=pid_state,
                u_min=limits.low,
                u_max=limits.high,
                du_max=du_lim,
            )
            d_hist.append(None)

        y_hist.append(y_meas)
        u_hist.append(u)
        plant = step_plant(plant, u, dt_s)

    y_arr = np.array(y_hist, dtype=float)
    u_arr = np.array(u_hist, dtype=float)
    d_arr: np.ndarray | None
    if controller == "mpc":
        d_arr = np.array([float(v) for v in d_hist], dtype=float)
    else:
        d_arr = None

    metrics = compute_metrics(
        time_s=time_s,
        y=y_arr,
        y_ref=y_ref,
        u_kw=u_arr,
        u_min=limits.low,
        u_max=limits.high,
        du_max=limits.max_step,
    )
    return SimulationResult(
        controller=controller,
        time_s=time_s,
        y_c=y_arr,
        y_ref=y_ref,
        u_kw=u_arr,
        d_hat=d_arr,
        metrics=metrics,
        active_constraints_last=active_last,
    )
