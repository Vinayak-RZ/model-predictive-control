"""Setpoint window and max-step limits used by the MPC solver.

In the Stamped product these are read from a line pack. Here the dataclass is
kept so the solver API matches the product code; callers pass illustrative
values. Nothing invents a default for an open threshold.
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
