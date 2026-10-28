"""Discrete PID on temperature tracking with anti-windup and actuator limits."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PIDGains:
    kp: float
    ki: float
    kd: float


@dataclass
class PIDState:
    integral: float = 0.0
    last_error: float = 0.0


def pid_step(
    *,
    y: float,
    y_ref: float,
    u_prev: float,
    dt_s: float,
    gains: PIDGains,
    state: PIDState,
    u_min: float,
    u_max: float,
    du_max: float | None = None,
) -> tuple[float, PIDState]:
    error = y_ref - y
    integral = state.integral + error * dt_s
    derivative = (error - state.last_error) / dt_s if dt_s > 0 else 0.0
    u_raw = u_prev + gains.kp * error + gains.ki * integral + gains.kd * derivative

    u_clipped = max(u_min, min(u_max, u_raw))
    if u_clipped != u_raw:
        # Back-calculate integral to reduce windup when saturated.
        if gains.ki != 0.0:
            integral = (u_clipped - u_prev - gains.kp * error - gains.kd * derivative) / gains.ki
    if du_max is not None:
        du = max(-du_max, min(du_max, u_clipped - u_prev))
        u_clipped = u_prev + du

    return u_clipped, PIDState(integral=integral, last_error=error)
