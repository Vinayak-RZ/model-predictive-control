"""Tests for scipy PID gain tuning."""

from __future__ import annotations

from mpc_core.sim.pid import PIDGains
from mpc_core.sim.pid_tune import tune_pid_gains
from mpc_core.sim.scenarios import SCENARIOS


def test_tune_pid_returns_finite_gains() -> None:
    scenario = SCENARIOS["setpoint_tracking"]
    result = tune_pid_gains(scenario, maxiter=8)
    assert result.gains.kp > 0
    assert result.metrics_iae >= 0
    assert result.violation_steps >= 0


def test_tuned_pid_runs_in_closed_loop() -> None:
    from mpc_core.sim.simulate import run_closed_loop

    scenario = SCENARIOS["disturbance_rejection"]
    tune = tune_pid_gains(scenario, maxiter=6)
    run = run_closed_loop(
        scenario,
        "pid",
        pid_gains=tune.gains,
        result_label="optimized_pid",
    )
    assert run.controller == "optimized_pid"
    assert isinstance(tune.gains, PIDGains)
