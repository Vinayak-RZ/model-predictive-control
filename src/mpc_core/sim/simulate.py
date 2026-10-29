"""Run MPC or PID against the heater plant for one scenario."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import time

from mpc_core import IdentifiedLinearModel, MpcState, SetpointLimits, solve
from mpc_core.sim.config import DemoConfig, default_demo_config
from mpc_core.sim.metrics import SimulationMetrics, compute_metrics
from mpc_core.sim.pid import PIDGains, PIDState, pid_step
from mpc_core.sim.plant import IBHPlantState, apply_disturbance_event, step_plant
from mpc_core.sim.scenarios import ScenarioConfig
from mpc_core.twin.ibh import IBHParams

ControllerKind = Literal["mpc", "pid"]


@dataclass(frozen=True)
class RunOptions:
    """Shared knobs so MPC, PID, and tuned PID see the same plant and noise."""

    noise_std_c: float = 0.0
    noise_seed: int = 42
    model_mismatch: bool = False
    enforce_pid_rate_limit: bool | None = None


@dataclass(frozen=True)
class SimulationResult:
    controller: ControllerKind | str
    time_s: np.ndarray
    y_c: np.ndarray
    y_ref: np.ndarray
    u_kw: np.ndarray
    d_hat: np.ndarray | None
    metrics: SimulationMetrics
    active_constraints_last: list[str]
    mpc_solve_ms: np.ndarray | None = None
    pid_gains: PIDGains | None = None


@dataclass(frozen=True)
class MpcStepSnapshot:
    step_index: int
    time_s: float
    y_meas: float
    y_ref: float
    u_applied: float
    d_hat: float
    predicted_y: list[float]
    planned_u: float
    solve_ms: float
    caption: str


@dataclass
class MpcStepLog:
    snapshots: list[MpcStepSnapshot] = field(default_factory=list)


def _reference_trace(scenario: ScenarioConfig, n_steps: int, dt_s: float) -> np.ndarray:
    time_s = np.arange(n_steps, dtype=float) * dt_s
    return scenario.y_ref_fn(time_s)


def _plant_params(cfg: DemoConfig, options: RunOptions) -> IBHParams:
    p = cfg.ibh
    if not options.model_mismatch:
        return p
    return IBHParams(
        m_kg=p.m_kg * 1.08,
        c_p_j_per_kg_k=p.c_p_j_per_kg_k,
        eta=p.eta * 0.94,
        U_w_per_k=p.U_w_per_k * 1.18,
        T_amb_c=p.T_amb_c,
    )


def _mpc_model(cfg: DemoConfig, options: RunOptions) -> IdentifiedLinearModel:
    """MPC always uses the nominal identified model; mismatch is plant-only."""
    _ = options
    return cfg.model


def run_closed_loop(
    scenario: ScenarioConfig,
    controller: ControllerKind,
    cfg: DemoConfig | None = None,
    *,
    horizon_steps: int | None = None,
    limits: SetpointLimits | None = None,
    options: RunOptions | None = None,
    pid_gains: PIDGains | None = None,
    mpc_tracking_weight: float = 1.0,
    result_label: str | None = None,
) -> SimulationResult:
    cfg = cfg or default_demo_config()
    opt = options or RunOptions()
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

    plant = IBHPlantState(T_c=scenario.t_initial_c, params=_plant_params(cfg, opt))
    u = scenario.u_initial_kw
    mpc_state = MpcState()
    pid_state = PIDState()
    base_gains = pid_gains or PIDGains(*scenario.pid_gains)
    gains = base_gains
    h = horizon_steps if horizon_steps is not None else (
        scenario.mpc_horizon if scenario.mpc_horizon else cfg.horizon_steps
    )
    model = _mpc_model(cfg, opt)

    rng = np.random.default_rng(opt.noise_seed)
    enforce_rate = (
        opt.enforce_pid_rate_limit
        if opt.enforce_pid_rate_limit is not None
        else scenario.pid_enforce_rate_limit
    )

    y_hist: list[float] = []
    u_hist: list[float] = []
    d_hist: list[float | None] = []
    active_last: list[str] = []
    solve_ms: list[float] = []

    for k in range(n_steps):
        t = time_s[k]
        y_true = plant.T_c
        noise = float(rng.normal(0.0, opt.noise_std_c)) if opt.noise_std_c > 0 else 0.0
        y_meas = y_true + noise
        y_r = float(y_ref[k])

        if (
            scenario.disturbance_at_s is not None
            and scenario.disturbance_event
            and t >= scenario.disturbance_at_s
        ):
            plant = apply_disturbance_event(plant, scenario.disturbance_event)

        if controller == "mpc":
            t0 = time.perf_counter()
            result = solve(
                model,
                [limits],
                {limits.setpoint_id: u},
                y_meas=y_meas,
                y_ref=y_r,
                horizon_steps=h,
                time_limit_s=cfg.solver_time_limit_s,
                state=mpc_state,
                tracking_weight=mpc_tracking_weight,
            )
            solve_ms.append((time.perf_counter() - t0) * 1000.0)
            u = float(np.clip(result.best[limits.setpoint_id], limits.low, limits.high))
            mpc_state = result.state
            active_last = list(result.active_constraints)
            d_hist.append(result.d_hat)
        else:
            du_lim = limits.max_step if enforce_rate else None
            u, pid_state = pid_step(
                y=y_meas,
                y_ref=y_r,
                u_prev=u,
                dt_s=dt_s,
                gains=gains,
                state=pid_state,
                u_min=limits.low,
                u_max=limits.high,
                du_max=du_lim,
            )
            u = float(np.clip(u, limits.low, limits.high))
            d_hist.append(None)

        y_hist.append(y_true)
        u_hist.append(u)
        plant = step_plant(plant, u, dt_s)

    y_arr = np.array(y_hist, dtype=float)
    u_arr = np.array(u_hist, dtype=float)
    d_arr: np.ndarray | None
    mpc_times: np.ndarray | None
    if controller == "mpc":
        d_arr = np.array([float(v) for v in d_hist], dtype=float)
        mpc_times = np.array(solve_ms, dtype=float)
    else:
        d_arr = None
        mpc_times = None

    metrics = compute_metrics(
        time_s=time_s,
        y=y_arr,
        y_ref=y_ref,
        u_kw=u_arr,
        u_min=limits.low,
        u_max=limits.high,
        du_max=limits.max_step if enforce_rate or controller == "mpc" else limits.max_step,
    )
    label: ControllerKind | str = result_label or controller

    return SimulationResult(
        controller=label,
        time_s=time_s,
        y_c=y_arr,
        y_ref=y_ref,
        u_kw=u_arr,
        d_hat=d_arr,
        metrics=metrics,
        active_constraints_last=active_last,
        mpc_solve_ms=mpc_times,
        pid_gains=gains if controller == "pid" else None,
    )


def run_mpc_step_log(
    scenario: ScenarioConfig,
    cfg: DemoConfig | None = None,
    *,
    horizon_steps: int | None = None,
    limits: SetpointLimits | None = None,
    options: RunOptions | None = None,
    max_steps: int | None = 80,
) -> MpcStepLog:
    """Record MPC predictions and the first move applied each sample (for teaching UI)."""
    cfg = cfg or default_demo_config()
    opt = options or RunOptions()
    dt_s = cfg.dt_s
    n_steps = int(scenario.duration_s / dt_s)
    if max_steps is not None:
        n_steps = min(n_steps, max_steps)
    time_s = np.arange(n_steps, dtype=float) * dt_s
    y_ref = _reference_trace(scenario, n_steps, dt_s)

    if limits is None:
        if scenario.limits_override:
            lo, hi, dmax = scenario.limits_override
            limits = SetpointLimits(cfg.limits.setpoint_id, cfg.limits.unit, lo, hi, dmax)
        else:
            limits = cfg.limits

    plant = IBHPlantState(T_c=scenario.t_initial_c, params=_plant_params(cfg, opt))
    u = scenario.u_initial_kw
    mpc_state = MpcState()
    h = horizon_steps if horizon_steps is not None else (
        scenario.mpc_horizon if scenario.mpc_horizon else cfg.horizon_steps
    )
    model = _mpc_model(cfg, opt)
    log = MpcStepLog()

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

        t0 = time.perf_counter()
        result = solve(
            model,
            [limits],
            {limits.setpoint_id: u},
            y_meas=y_meas,
            y_ref=y_r,
            horizon_steps=h,
            time_limit_s=cfg.solver_time_limit_s,
            state=mpc_state,
            tracking_weight=1.0,
        )
        ms = (time.perf_counter() - t0) * 1000.0
        u_new = float(np.clip(result.best[limits.setpoint_id], limits.low, limits.high))
        caption = (
            f"At t={t:.0f}s the measured temperature is {y_meas:.1f}°C. "
            f"MPC plans power {u_new:.1f} kW over the next {h} steps; "
            f"only that first move is applied, then the horizon shifts."
        )
        if result.active_constraints:
            caption += f" Active limits: {', '.join(result.active_constraints)}."
        log.snapshots.append(
            MpcStepSnapshot(
                step_index=k,
                time_s=t,
                y_meas=y_meas,
                y_ref=y_r,
                u_applied=u_new,
                d_hat=result.d_hat,
                predicted_y=list(result.predicted_y),
                planned_u=u_new,
                solve_ms=ms,
                caption=caption,
            )
        )
        u = u_new
        mpc_state = result.state
        plant = step_plant(plant, u, dt_s)

    return log
