"""Tests for closed-loop simulation helpers."""

from __future__ import annotations

import numpy as np

from mpc_core.sim.metrics import compute_metrics
from mpc_core.sim.scenarios import SCENARIOS
from mpc_core.sim.simulate import run_closed_loop


def test_run_closed_loop_mpc_and_pid_finite() -> None:
    scenario = SCENARIOS["setpoint_tracking"]
    mpc = run_closed_loop(scenario, "mpc")
    pid = run_closed_loop(scenario, "pid")
    assert len(mpc.time_s) == len(mpc.y_c) == len(mpc.u_kw)
    assert len(pid.time_s) == len(pid.y_c) == len(pid.u_kw)
    assert np.all(np.isfinite(mpc.y_c))
    assert np.all(np.isfinite(pid.y_c))


def test_power_constraints_pid_may_violate_rate_limit() -> None:
    scenario = SCENARIOS["power_constraints"]
    mpc = run_closed_loop(scenario, "mpc")
    pid = run_closed_loop(scenario, "pid")
    assert mpc.metrics.constraint_violation_steps == 0
    assert pid.metrics.constraint_violation_steps >= 1


def test_compute_metrics_basic() -> None:
    t = np.array([0.0, 1.0, 2.0])
    y = np.array([0.0, 1.0, 2.0])
    ref = np.array([2.0, 2.0, 2.0])
    u = np.array([1.0, 1.0, 1.0])
    m = compute_metrics(
        time_s=t,
        y=y,
        y_ref=ref,
        u_kw=u,
        u_min=0.0,
        u_max=5.0,
        du_max=1.0,
    )
    assert m.iae >= 0.0
    assert m.ise >= 0.0
