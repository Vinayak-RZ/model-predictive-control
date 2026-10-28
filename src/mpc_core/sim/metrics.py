"""Performance metrics for closed-loop runs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SimulationMetrics:
    iae: float
    ise: float
    overshoot_pct: float
    settling_time_s: float | None
    constraint_violation_steps: int
    energy_kwh: float


def compute_metrics(
    *,
    time_s: np.ndarray,
    y: np.ndarray,
    y_ref: np.ndarray,
    u_kw: np.ndarray,
    u_min: float,
    u_max: float,
    du_max: float | None,
    settling_band_pct: float = 3.0,
) -> SimulationMetrics:
    dt = np.diff(time_s, prepend=time_s[0])
    if len(time_s) > 1:
        dt[0] = time_s[1] - time_s[0]
    error = y_ref - y
    iae = float(np.sum(np.abs(error) * dt))
    ise = float(np.sum(error**2 * dt))

    # Overshoot relative to final reference segment (last 20% mean).
    tail_ref = float(np.mean(y_ref[int(len(y_ref) * 0.8) :]))
    if abs(tail_ref) > 1e-6:
        if tail_ref >= np.max(y_ref[: max(1, len(y_ref) // 5)]):
            peak = float(np.max(y))
            overshoot = max(0.0, (peak - tail_ref) / abs(tail_ref) * 100.0)
        else:
            trough = float(np.min(y))
            overshoot = max(0.0, (tail_ref - trough) / abs(tail_ref) * 100.0)
    else:
        overshoot = 0.0

    band = abs(tail_ref) * settling_band_pct / 100.0 if abs(tail_ref) > 1e-6 else 0.5
    settling: float | None = None
    for i in range(len(y) - 1, -1, -1):
        if abs(y[i] - tail_ref) > band:
            settling = float(time_s[min(i + 1, len(time_s) - 1)])
            break

    violations = 0
    for i, ui in enumerate(u_kw):
        if ui < u_min - 1e-9 or ui > u_max + 1e-9:
            violations += 1
        if du_max is not None and i > 0:
            if abs(ui - u_kw[i - 1]) > du_max + 1e-6:
                violations += 1

    energy_kwh = float(np.sum(u_kw * dt) / 3600.0)
    return SimulationMetrics(
        iae=iae,
        ise=ise,
        overshoot_pct=overshoot,
        settling_time_s=settling,
        constraint_violation_steps=violations,
        energy_kwh=energy_kwh,
    )
