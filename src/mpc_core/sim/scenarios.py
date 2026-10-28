"""Named scenarios for coursework comparisons."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from mpc_core.sim.config import DemoConfig, default_demo_config


@dataclass(frozen=True)
class ScenarioConfig:
    key: str
    title: str
    description: str
    duration_s: int
    t_initial_c: float
    u_initial_kw: float
    y_ref_fn: Callable[[np.ndarray], np.ndarray]
    disturbance_at_s: float | None = None
    disturbance_event: str | None = None
    limits_override: tuple[float, float, float] | None = None
    pid_gains: tuple[float, float, float] = (2.8, 0.04, 0.0)
    mpc_horizon: int | None = None
    pid_enforce_rate_limit: bool = True


def _ref_step_80_120(time_s: np.ndarray) -> np.ndarray:
    ref = np.full_like(time_s, 80.0, dtype=float)
    ref[time_s >= 30.0] = 120.0
    return ref


def _ref_step_90_115(time_s: np.ndarray) -> np.ndarray:
    ref = np.full_like(time_s, 90.0, dtype=float)
    ref[time_s >= 20.0] = 115.0
    return ref


def _ref_aggressive_high(time_s: np.ndarray) -> np.ndarray:
    ref = np.full_like(time_s, 85.0, dtype=float)
    ref[time_s >= 15.0] = 165.0
    return ref


def build_scenarios(cfg: DemoConfig | None = None) -> dict[str, ScenarioConfig]:
    _ = cfg or default_demo_config()
    return {
        "setpoint_tracking": ScenarioConfig(
            key="setpoint_tracking",
            title="Setpoint tracking",
            description=(
                "Temperature setpoint steps from 80 °C to 120 °C at 30 s. "
                "Compares how quickly each controller reaches the new target."
            ),
            duration_s=180,
            t_initial_c=80.0,
            u_initial_kw=95.0,
            y_ref_fn=_ref_step_80_120,
        ),
        "disturbance_rejection": ScenarioConfig(
            key="disturbance_rejection",
            title="Disturbance rejection",
            description=(
                "At 70 s the effective heat loss increases (U step) while the "
                "setpoint stays at 115 °C. Offset-free MPC updates its disturbance "
                "estimate; PID must react only through feedback."
            ),
            duration_s=200,
            t_initial_c=90.0,
            u_initial_kw=110.0,
            y_ref_fn=_ref_step_90_115,
            disturbance_at_s=70.0,
            disturbance_event="heat_loss_bump",
            pid_gains=(3.2, 0.05, 0.5),
        ),
        "power_constraints": ScenarioConfig(
            key="power_constraints",
            title="Power limits and rate constraints",
            description=(
                "Tight power cap (150 kW) and 8 kW/s move limit while requesting "
                "165 °C. MPC anticipates the ceiling; PID often saturates and "
                "overshoots when limits bind."
            ),
            duration_s=200,
            t_initial_c=85.0,
            u_initial_kw=100.0,
            y_ref_fn=_ref_aggressive_high,
            limits_override=(0.0, 150.0, 8.0),
            pid_gains=(4.5, 0.08, 0.0),
            mpc_horizon=30,
            pid_enforce_rate_limit=False,
        ),
    }


SCENARIOS = build_scenarios()
