"""Offset-free MPC on an identified linear model (W5.1, shadow).

Integrating disturbance per Pannocchia and Rawlings (2003). The disturbance is
refreshed each run from the one-step innovation (full correction, no separate
observer gain). The quadratic programme tracks a CV reference under the line-pack
window and max-step; there is no move-weight term so nothing is invented.
Decision variables are successive input increments (move blocking): ``n_u`` free
moves, then the last input is held for the rest of the horizon. Only the first
move is applied. Horizon and solver time limit come from the caller. Nothing
here writes to a plant.
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

# Default: one free move held across the horizon (fast, strong on this plant).
# Callers may raise n_u for a richer plan; rate limits stay hard via Δu bounds.
_DEFAULT_N_U = 1
_TERMINAL_SCALE = 2.5


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


def _deltas_to_sequence(
    deltas: NDArray[np.float64],
    u0: float,
    horizon_steps: int,
    window_lo: float,
    window_hi: float,
) -> NDArray[np.float64]:
    """Integrate Δu moves, clip to the power window, hold the last free value."""
    n_u = len(deltas)
    u_free = np.empty(n_u, dtype=np.float64)
    u = u0
    for k, du in enumerate(deltas):
        u = float(np.clip(u + float(du), window_lo, window_hi))
        u_free[k] = u
    if n_u >= horizon_steps:
        return u_free[:horizon_steps]
    u_seq = np.empty(horizon_steps, dtype=np.float64)
    u_seq[:n_u] = u_free
    u_seq[n_u:] = u_free[-1]
    return u_seq


def _simulate(
    model: IdentifiedLinearModel,
    y0: float,
    d_hat: float,
    u_seq: NDArray[np.float64],
) -> NDArray[np.float64]:
    y = y0
    out = np.empty(len(u_seq), dtype=np.float64)
    a = float(model.a)
    b = float(model.b)
    for i, u in enumerate(u_seq):
        y = a * y + b * float(u) + d_hat
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
    n_u_moves: int | None = None,
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
    window_lo = float(lim.low)
    window_hi = float(lim.high)
    du_max = float(lim.max_step)
    if window_lo > window_hi:
        raise ValueError("empty power window")
    first_lo = max(window_lo, u0 - du_max)
    first_hi = min(window_hi, u0 + du_max)
    if first_lo > first_hi:
        raise ValueError("no feasible setting within one step of the current setting")

    h = int(horizon_steps)
    n_u = int(n_u_moves) if n_u_moves is not None else _DEFAULT_N_U
    n_u = max(1, min(n_u, h))
    term_start = max(0, (2 * h) // 3)

    deadline = time.monotonic() + time_limit_s

    def f(x: NDArray[np.float64]) -> float:
        if time.monotonic() > deadline:
            raise MpcTimedOut()
        deltas = np.asarray(x, dtype=np.float64)
        u_seq = _deltas_to_sequence(deltas, u0, h, window_lo, window_hi)
        ys = _simulate(model, y_meas, st.d_hat, u_seq)
        err = ys - y_ref
        weights = np.ones(h, dtype=np.float64)
        weights[term_start:] = _TERMINAL_SCALE
        return tracking_weight * float(np.dot(weights, err * err))

    bounds = [(-du_max, du_max)] * n_u

    if abs(model.b) < 1e-12:
        u_ss = u0
    else:
        u_ss = ((1.0 - model.a) * y_ref - st.d_hat) / model.b
    u_ss = float(np.clip(u_ss, window_lo, window_hi))
    x0 = np.zeros(n_u, dtype=np.float64)
    remaining = u_ss - u0
    for k in range(n_u):
        step = float(np.clip(remaining, -du_max, du_max))
        x0[k] = step
        remaining -= step

    res = minimize(
        f,
        x0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": 80, "ftol": 1e-12},
    )
    deltas = np.asarray(res.x, dtype=np.float64)
    u_seq = _deltas_to_sequence(deltas, u0, h, window_lo, window_hi)
    u_star = float(np.clip(u_seq[0], first_lo, first_hi))
    u_seq = u_seq.copy()
    u_seq[0] = u_star
    ys = _simulate(model, y_meas, st.d_hat, u_seq)
    active: list[str] = []
    if np.isclose(u_star, lim.low) or np.isclose(u_star, lim.high):
        active.append(f"{sp}.window")
    if np.isclose(abs(u_star - u0), lim.max_step):
        active.append(f"{sp}.max_step")
    st_out = MpcState(d_hat=st.d_hat, last_y=y_meas, last_u=u_star)
    return MpcResult(
        best={sp: u_star},
        y_ref=y_ref,
        d_hat=st.d_hat,
        predicted_y=[float(v) for v in ys],
        active_constraints=active,
        state=st_out,
    )
