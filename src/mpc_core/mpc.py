"""Offset-free MPC on an identified linear model (W5.1, shadow).

Integrating disturbance per Pannocchia and Rawlings (2003). The disturbance is
refreshed each run from the one-step innovation (full correction, no separate
observer gain). The quadratic programme tracks a CV reference under the line-pack
window and max-step; there is no move-weight term so nothing is invented.
Horizon and solver time limit come from the module record; open values abstain.
Nothing here writes to a plant.
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

from mpc_core.identified import IdentifiedLinearModel
from mpc_core.thresholds import SetpointLimits


class MpcTimedOut(Exception):
    pass


@dataclass
class MpcState:
    """Carried across shadow runs for the integrating disturbance."""

    d_hat: float = 0.0
    last_y: float | None = None
    last_u: float | None = None


@dataclass(frozen=True)
class MpcResult:
    best: dict[str, float]
    y_ref: float
    d_hat: float
    predicted_y: list[float]
    active_constraints: list[str]
    state: MpcState


def refresh_disturbance(
    model: IdentifiedLinearModel,
    state: MpcState,
    y_meas: float,
    u_current: float,
) -> MpcState:
    """Update integrating disturbance from the one-step innovation."""
    if state.last_y is None or state.last_u is None:
        # Steady-state initialisation: y = a y + b u + d  =>  d = (1-a)y - b u.
        d0 = (1.0 - model.a) * y_meas - model.b * u_current
        return MpcState(d_hat=d0, last_y=y_meas, last_u=u_current)
    y_pred = model.a * state.last_y + model.b * state.last_u + state.d_hat
    return MpcState(
        d_hat=state.d_hat + (y_meas - y_pred),
        last_y=y_meas,
        last_u=u_current,
    )


def _simulate(
    model: IdentifiedLinearModel,
    y0: float,
    d_hat: float,
    u_seq: NDArray[np.float64],
) -> NDArray[np.float64]:
    y = y0
    out = np.empty(len(u_seq), dtype=np.float64)
    for i, u in enumerate(u_seq):
        y = model.a * y + model.b * float(u) + d_hat
        out[i] = y
    return out


def solve(
    model: IdentifiedLinearModel,
    limits: Sequence[SetpointLimits],
    current: Mapping[str, float],
    y_meas: float,
    y_ref: float,
    horizon_steps: int,
    time_limit_s: float,
    state: MpcState,
    tracking_weight: float = 1.0,
) -> MpcResult:
    """SISO offset-free QP over ``horizon_steps``; returns the first-move proposal."""
    if horizon_steps < 1:
        raise ValueError("horizon_steps must be at least 1")
    if len(limits) != 1:
        raise ValueError("identified_linear offset-free MPC is SISO in W5.1")
    lim = limits[0]
    sp = lim.setpoint_id
    u0 = float(current[sp])
    st = refresh_disturbance(model, state, y_meas, u0)
    lo = max(lim.low, u0 - lim.max_step)
    hi = min(lim.high, u0 + lim.max_step)
    if lo > hi:
        raise ValueError("no feasible setting within one step of the current setting")

    # Decision variables: held input for the whole horizon (single degree of freedom
    # for SISO shadow). Multi-move free sequences can follow once a move-weight is set.
    deadline = time.monotonic() + time_limit_s

    def f(x: NDArray[np.float64]) -> float:
        if time.monotonic() > deadline:
            raise MpcTimedOut()
        u = float(x[0])
        u_seq = np.full(horizon_steps, u, dtype=np.float64)
        ys = _simulate(model, y_meas, st.d_hat, u_seq)
        return tracking_weight * float(np.sum((ys - y_ref) ** 2))

    x0 = np.array([float(np.clip(u0, lo, hi))], dtype=np.float64)
    res = minimize(f, x0, method="L-BFGS-B", bounds=[(lo, hi)])
    u_star = float(np.asarray(res.x, dtype=np.float64)[0])
    u_seq = np.full(horizon_steps, u_star, dtype=np.float64)
    ys = _simulate(model, y_meas, st.d_hat, u_seq)
    active: list[str] = []
    if np.isclose(u_star, lim.low) or np.isclose(u_star, lim.high):
        active.append(f"{sp}.window")
    elif np.isclose(abs(u_star - u0), lim.max_step):
        active.append(f"{sp}.max_step")
    st_out = MpcState(d_hat=st.d_hat, last_y=y_meas, last_u=u_star)
    proposed = {sp: u_star} if u_star != u0 else {}
    return MpcResult(
        best=proposed if proposed else {sp: u_star},
        y_ref=y_ref,
        d_hat=st.d_hat,
        predicted_y=[float(v) for v in ys],
        active_constraints=active,
        state=st_out,
    )
