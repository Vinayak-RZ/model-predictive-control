"""Tests for PID with measured load feedforward."""

from __future__ import annotations

from mpc_core.sim.scenarios import SCENARIOS
from mpc_core.sim.simulate import run_closed_loop


def test_optimized_pid_feedforward_runs_on_disturbance() -> None:
    scenario = SCENARIOS["disturbance_rejection"]
    base = run_closed_loop(scenario, "pid")
    ff = run_closed_loop(
        scenario,
        "pid",
        pid_measured_feedforward=True,
    )
    assert base.metrics.iae > 0.0
    assert ff.metrics.iae > 0.0
