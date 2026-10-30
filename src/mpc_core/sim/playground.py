"""Build ad-hoc scenarios and run three-controller comparisons for the Streamlit UI."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

import numpy as np

from mpc_core.sim.config import DemoConfig, default_demo_config
from mpc_core.sim.pid import PIDGains
from mpc_core.sim.pid_tune import TuneResult, tune_pid_gains
from mpc_core.sim.scenarios import ScenarioConfig
from mpc_core.sim.simulate import RunOptions, SimulationResult, run_closed_loop
from mpc_core.thresholds import SetpointLimits


@dataclass(frozen=True)
class PlaygroundParams:
    duration_s: int = 180
    t_initial_c: float = 80.0
    u_initial_kw: float = 95.0
    ref_low_c: float = 80.0
    ref_high_c: float = 120.0
    ref_step_at_s: float = 30.0
    disturbance_at_s: float | None = None
    disturbance_event: str | None = None
    u_min: float = 0.0
    u_max: float = 250.0
    du_max: float = 25.0
    noise_std_c: float = 0.0
    noise_seed: int = 42
    model_mismatch: bool = False
    mpc_horizon: int = 40
    mpc_tracking_weight: float = 1.0
    pid_kp: float = 2.8
    pid_ki: float = 0.04
    pid_kd: float = 0.0
    enforce_pid_rate: bool = True


def build_playground_scenario(p: PlaygroundParams) -> ScenarioConfig:
    def y_ref_fn(time_s: np.ndarray) -> np.ndarray:
        ref = np.full_like(time_s, p.ref_low_c, dtype=float)
        ref[time_s >= p.ref_step_at_s] = p.ref_high_c
        return ref

    return ScenarioConfig(
        key="playground",
        title="Playground",
        description="Interactive scenario from the Playground sliders.",
        duration_s=p.duration_s,
        t_initial_c=p.t_initial_c,
        u_initial_kw=p.u_initial_kw,
        y_ref_fn=y_ref_fn,
        disturbance_at_s=p.disturbance_at_s,
        disturbance_event=p.disturbance_event,
        limits_override=(p.u_min, p.u_max, p.du_max),
        pid_gains=(p.pid_kp, p.pid_ki, p.pid_kd),
        mpc_horizon=p.mpc_horizon,
        pid_enforce_rate_limit=p.enforce_pid_rate,
    )


def run_options_from_playground(p: PlaygroundParams) -> RunOptions:
    return RunOptions(
        noise_std_c=p.noise_std_c,
        noise_seed=p.noise_seed,
        model_mismatch=p.model_mismatch,
        enforce_pid_rate_limit=p.enforce_pid_rate,
    )


def limits_from_playground(p: PlaygroundParams, cfg: DemoConfig | None = None) -> SetpointLimits:
    cfg = cfg or default_demo_config()
    return SetpointLimits(
        cfg.limits.setpoint_id,
        cfg.limits.unit,
        p.u_min,
        p.u_max,
        p.du_max,
    )


@dataclass(frozen=True)
class TripleRun:
    mpc: SimulationResult
    pid: SimulationResult
    optimized_pid: SimulationResult
    tune: TuneResult


# Gains tuned once on the mild setpoint jump, then reused everywhere. That matches
# field practice (you do not retune PID for every door-open) and lets MPC's
# constraint planning show up against a strong but fixed PID baseline.
_BASELINE_OPT_PID: TuneResult | None = None


def baseline_optimized_pid(
    *,
    cfg: DemoConfig | None = None,
    tune_maxiter: int = 35,
) -> TuneResult:
    """Return Opt. PID gains locked to the setpoint-tracking scenario.

    Tuned for tracking on the mild jump (no rate enforcement in the tune loop,
    no violation penalty) so the baseline is a strong tracker — then frozen and
    stressed on tight-limit presets where MPC keeps the slew feasible.
    """
    global _BASELINE_OPT_PID
    if _BASELINE_OPT_PID is not None:
        return _BASELINE_OPT_PID
    from mpc_core.sim.scenarios import SCENARIOS

    cfg = cfg or default_demo_config()
    _BASELINE_OPT_PID = tune_pid_gains(
        SCENARIOS["setpoint_tracking"],
        cfg=cfg,
        options=RunOptions(enforce_pid_rate_limit=False),
        violation_weight=0.0,
        maxiter=tune_maxiter,
    )
    return _BASELINE_OPT_PID


def run_triple(
    scenario: ScenarioConfig,
    *,
    cfg: DemoConfig | None = None,
    limits: SetpointLimits | None = None,
    options: RunOptions | None = None,
    horizon_steps: int | None = None,
    mpc_tracking_weight: float = 1.0,
    plain_pid_gains: PIDGains | None = None,
    tune_maxiter: int = 35,
    freeze_optimized_pid: bool = True,
) -> TripleRun:
    cfg = cfg or default_demo_config()
    opt = options or RunOptions()
    plain = plain_pid_gains or PIDGains(*scenario.pid_gains)
    if freeze_optimized_pid:
        tune = baseline_optimized_pid(cfg=cfg, tune_maxiter=tune_maxiter)
    else:
        tune = tune_pid_gains(
            scenario,
            cfg=cfg,
            limits=limits,
            options=opt,
            x0=(plain.kp, plain.ki, plain.kd),
            maxiter=tune_maxiter,
        )
    mpc = run_closed_loop(
        scenario,
        "mpc",
        cfg=cfg,
        horizon_steps=horizon_steps,
        limits=limits,
        options=opt,
        mpc_tracking_weight=mpc_tracking_weight,
    )
    pid = run_closed_loop(
        scenario,
        "pid",
        cfg=cfg,
        limits=limits,
        options=opt,
        pid_gains=plain,
        result_label="pid",
    )
    opt_pid = run_closed_loop(
        scenario,
        "pid",
        cfg=cfg,
        limits=limits,
        options=opt,
        pid_gains=tune.gains,
        result_label="optimized_pid",
    )
    return TripleRun(mpc=mpc, pid=pid, optimized_pid=opt_pid, tune=tune)


PRESETS: dict[str, Callable[[PlaygroundParams], PlaygroundParams]] = {
    "setpoint_jump": lambda p: replace(
        p,
        ref_low_c=80.0,
        ref_high_c=120.0,
        ref_step_at_s=30.0,
        disturbance_at_s=None,
        disturbance_event=None,
    ),
    "cold_door": lambda p: replace(
        p,
        disturbance_at_s=70.0,
        disturbance_event="ambient_step",
        ref_low_c=90.0,
        ref_high_c=115.0,
        ref_step_at_s=20.0,
    ),
    "heat_loss_noise": lambda p: replace(
        p,
        disturbance_at_s=70.0,
        disturbance_event="heat_loss_bump",
        ref_low_c=90.0,
        ref_high_c=115.0,
        ref_step_at_s=20.0,
        noise_std_c=0.85,
        noise_seed=7,
        mpc_horizon=28,
        mpc_tracking_weight=1.4,
    ),
    "tight_power": lambda p: replace(
        p,
        u_max=140.0,
        du_max=6.0,
        ref_low_c=85.0,
        ref_high_c=155.0,
        ref_step_at_s=15.0,
        mpc_horizon=45,
        # PID may break the slew; MPC still respects it in the plan.
        enforce_pid_rate=False,
    ),
    "model_mismatch": lambda p: replace(p, model_mismatch=True, ref_step_at_s=25.0),
    "soft_limits": lambda p: replace(
        p,
        u_max=220.0,
        du_max=18.0,
        ref_low_c=80.0,
        ref_high_c=130.0,
        ref_step_at_s=25.0,
        disturbance_at_s=None,
        disturbance_event=None,
        model_mismatch=False,
        noise_std_c=0.25,
        pid_kp=3.6,
        pid_ki=0.06,
        pid_kd=0.4,
        mpc_horizon=20,
        mpc_tracking_weight=0.8,
    ),
}
