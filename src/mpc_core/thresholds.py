"""Setpoint window and max-step limits used by the MPC solver.

Callers supply bounds explicitly for each scenario; nothing invents a default
for an open threshold.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SetpointLimits:
    """Bounds for one writable setpoint."""

    setpoint_id: str
    unit: str
    low: float
    high: float
    max_step: float
