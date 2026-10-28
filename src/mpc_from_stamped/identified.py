"""Identified linear model record for the MPC identification gate (C27).

Coefficients come from a plant-sim or historian identification experiment.
This module never invents them. The runner refuses MPC without a matching
fit and a valid model card (see model_card.py).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IdentifiedLinearModel:
    """SISO discrete model y[k+1] = a*y[k] + b*u[k]."""

    fit_id: str
    a: float
    b: float
    dt_s: float
    n_samples: int
    residual_rms: float
    experiment: str

    def __post_init__(self) -> None:
        if not self.fit_id:
            raise ValueError("fit_id is required")
        if self.dt_s <= 0:
            raise ValueError("dt_s must be positive")
        if self.n_samples < 3:
            raise ValueError("n_samples must be at least 3")
        if self.b == 0.0:
            raise ValueError("b must be non-zero (no input effect)")
