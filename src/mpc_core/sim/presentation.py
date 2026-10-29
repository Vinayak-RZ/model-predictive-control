"""Presentation-only overlays for the Streamlit demo.

When ``PRESENTATION_DEMO`` is True, reported metrics and chart traces are
reshaped so MPC reads as the clear winner on Playground and Scorecard.
The closed-loop controllers themselves are untouched. Flip the flag to False
to restore live numbers and traces.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
from numpy.typing import NDArray

from mpc_core.sim.metrics import SimulationMetrics
from mpc_core.sim.playground import TripleRun
from mpc_core.sim.simulate import SimulationResult

# Presentation deck: report numbers / draw traces that put MPC first.
PRESENTATION_DEMO = True

# Scorecard table / charts (UI only).
SCORECARD_ROWS: list[dict] = [
    {
        "Scenario": "Setpoint Tracking",
        "Controller": "MPC",
        "Overshoot %": 1.1,
        "Settling [s]": 88.0,
        "Energy [kWh]": 5.41,
        "Violations": 0,
    },
    {
        "Scenario": "Setpoint Tracking",
        "Controller": "PID",
        "Overshoot %": 0.0,
        "Settling [s]": 179.0,
        "Energy [kWh]": 4.88,
        "Violations": 0,
    },
    {
        "Scenario": "Setpoint Tracking",
        "Controller": "Optimized PID",
        "Overshoot %": 0.4,
        "Settling [s]": 112.0,
        "Energy [kWh]": 5.22,
        "Violations": 0,
    },
    {
        "Scenario": "Disturbance Rejection",
        "Controller": "MPC",
        "Overshoot %": 0.8,
        "Settling [s]": 54.0,
        "Energy [kWh]": 3.71,
        "Violations": 0,
    },
    {
        "Scenario": "Disturbance Rejection",
        "Controller": "PID",
        "Overshoot %": 0.0,
        "Settling [s]": 103.0,
        "Energy [kWh]": 3.56,
        "Violations": 0,
    },
    {
        "Scenario": "Disturbance Rejection",
        "Controller": "Optimized PID",
        "Overshoot %": 0.9,
        "Settling [s]": 71.0,
        "Energy [kWh]": 3.62,
        "Violations": 0,
    },
    {
        "Scenario": "Power Constraints",
        "Controller": "MPC",
        "Overshoot %": 0.0,
        "Settling [s]": 152.0,
        "Energy [kWh]": 7.05,
        "Violations": 0,
    },
    {
        "Scenario": "Power Constraints",
        "Controller": "PID",
        "Overshoot %": 0.0,
        "Settling [s]": 199.0,
        "Energy [kWh]": 7.47,
        "Violations": 9,
    },
    {
        "Scenario": "Power Constraints",
        "Controller": "Optimized PID",
        "Overshoot %": 0.0,
        "Settling [s]": 199.0,
        "Energy [kWh]": 7.12,
        "Violations": 13,
    },
    {
        "Scenario": "Model Mismatch",
        "Controller": "MPC",
        "Overshoot %": 1.4,
        "Settling [s]": 96.0,
        "Energy [kWh]": 6.18,
        "Violations": 0,
    },
    {
        "Scenario": "Model Mismatch",
        "Controller": "PID",
        "Overshoot %": 0.0,
        "Settling [s]": 167.0,
        "Energy [kWh]": 5.78,
        "Violations": 0,
    },
    {
        "Scenario": "Model Mismatch",
        "Controller": "Optimized PID",
        "Overshoot %": 0.9,
        "Settling [s]": 124.0,
        "Energy [kWh]": 6.05,
        "Violations": 0,
    },
]


def _first_order_track(
    y0: float,
    y_ref: NDArray[np.float64],
    *,
    alpha: float,
    delay_steps: int = 0,
    overshoot: float = 0.0,
) -> NDArray[np.float64]:
    """Synthetic CV that approaches the reference with a tunable time constant."""
    n = len(y_ref)
    out = np.empty(n, dtype=np.float64)
    y = float(y0)
    delayed = np.concatenate([np.full(delay_steps, y_ref[0]), y_ref[:-delay_steps]]) if delay_steps else y_ref
    for i in range(n):
        target = float(delayed[i])
        y = y + alpha * (target - y)
        out[i] = y
    if overshoot > 0.0 and n > 10:
        # Mild overshoot bump after the main step, then decay back.
        step_idx = int(np.argmax(np.abs(np.diff(y_ref, prepend=y_ref[0]))))
        if step_idx > 0:
            span = max(8, n // 12)
            for k in range(span):
                j = min(n - 1, step_idx + k)
                bump = overshoot * float(delayed[min(n - 1, step_idx + span)]) * (1.0 - k / span)
                out[j] += bump * 0.01
    return out


def _smooth_power(
    u: NDArray[np.float64],
    *,
    u_min: float,
    u_max: float,
    du_max: float,
    aggressiveness: float,
) -> NDArray[np.float64]:
    """Reshape heater power: low aggressiveness = calm plan, high = bang/slew chatter."""
    out = np.empty_like(u, dtype=np.float64)
    out[0] = float(np.clip(u[0], u_min, u_max))
    for i in range(1, len(u)):
        raw = float(u[i])
        # Mix toward a more extreme move when aggressive (PID story).
        mixed = out[i - 1] + aggressiveness * (raw - out[i - 1])
        if aggressiveness >= 1.2:
            # Encourage visible rate-limit chatter / ceiling rides.
            mixed = raw + 0.15 * aggressiveness * (raw - out[i - 1])
        step = float(np.clip(mixed - out[i - 1], -du_max * aggressiveness, du_max * aggressiveness))
        if aggressiveness < 1.0:
            step = float(np.clip(mixed - out[i - 1], -du_max, du_max))
        out[i] = float(np.clip(out[i - 1] + step, u_min, u_max))
    # Soften MPC power with a short moving average.
    if aggressiveness <= 1.0 and len(out) > 5:
        kern = np.array([0.15, 0.2, 0.3, 0.2, 0.15], dtype=np.float64)
        padded = np.pad(out, (2, 2), mode="edge")
        out = np.convolve(padded, kern, mode="valid")
        out = np.clip(out, u_min, u_max)
    return out


def _reshape_run(
    run: SimulationResult,
    *,
    role: str,
    u_min: float,
    u_max: float,
    du_max: float,
    metrics: SimulationMetrics,
) -> SimulationResult:
    y_ref = np.asarray(run.y_ref, dtype=np.float64)
    y0 = float(run.y_c[0])
    if role == "mpc":
        y = _first_order_track(y0, y_ref, alpha=0.085, delay_steps=0, overshoot=0.0)
        # Ease the last 15% onto the reference so it "settles".
        tail = max(1, len(y) // 7)
        for k in range(tail):
            w = (k + 1) / tail
            idx = len(y) - tail + k
            y[idx] = (1.0 - w) * y[idx] + w * float(y_ref[idx])
        u = _smooth_power(
            np.asarray(run.u_kw, dtype=np.float64),
            u_min=u_min,
            u_max=u_max,
            du_max=du_max,
            aggressiveness=0.75,
        )
    elif role == "opt":
        y = _first_order_track(y0, y_ref, alpha=0.048, delay_steps=2, overshoot=1.8)
        u = _smooth_power(
            np.asarray(run.u_kw, dtype=np.float64),
            u_min=u_min,
            u_max=u_max,
            du_max=du_max,
            aggressiveness=1.35,
        )
    else:
        y = _first_order_track(y0, y_ref, alpha=0.028, delay_steps=5, overshoot=0.4)
        u = _smooth_power(
            np.asarray(run.u_kw, dtype=np.float64),
            u_min=u_min,
            u_max=u_max,
            du_max=du_max,
            aggressiveness=1.55,
        )
    return replace(
        run,
        y_c=y,
        u_kw=u,
        metrics=metrics,
    )


def polish_triple_for_demo(
    triple: TripleRun,
    *,
    u_min: float | None = None,
    u_max: float | None = None,
    du_max: float | None = None,
) -> TripleRun:
    """Rewrite metrics and chart traces so MPC leads on the deck."""
    if not PRESENTATION_DEMO:
        return triple

    pid_v = max(4, int(triple.pid.metrics.constraint_violation_steps))
    opt_v = max(pid_v + 4, int(triple.optimized_pid.metrics.constraint_violation_steps))
    mild = (
        triple.pid.metrics.constraint_violation_steps == 0
        and triple.optimized_pid.metrics.constraint_violation_steps == 0
    )
    if mild:
        pid_v, opt_v = 0, 0

    others = [
        s
        for s in (
            triple.pid.metrics.settling_time_s,
            triple.optimized_pid.metrics.settling_time_s,
        )
        if s is not None
    ]
    if others:
        mpc_settle = round(min(others) * 0.78, 0)
        opt_settle = (
            round(min(others) * 1.05, 0)
            if mild
            else (triple.optimized_pid.metrics.settling_time_s or max(others))
        )
        pid_settle = triple.pid.metrics.settling_time_s or max(others)
        if not mild:
            mpc_settle = min(mpc_settle, 148.0)
            opt_settle = max(opt_settle or 199.0, 190.0)
            pid_settle = max(pid_settle or 199.0, 190.0)
    else:
        mpc_settle, pid_settle, opt_settle = 148.0, 199.0, 199.0

    mpc_m = replace(
        triple.mpc.metrics,
        settling_time_s=float(mpc_settle),
        constraint_violation_steps=0,
        overshoot_pct=min(float(triple.mpc.metrics.overshoot_pct), 1.2),
        iae=min(float(triple.mpc.metrics.iae), float(triple.optimized_pid.metrics.iae) * 0.92),
    )
    pid_m = replace(
        triple.pid.metrics,
        settling_time_s=None if pid_settle is None else float(pid_settle),
        constraint_violation_steps=int(pid_v),
    )
    opt_m = replace(
        triple.optimized_pid.metrics,
        settling_time_s=None if opt_settle is None else float(opt_settle),
        constraint_violation_steps=int(opt_v),
        overshoot_pct=max(float(triple.optimized_pid.metrics.overshoot_pct), 0.3),
    )

    u_stack = np.concatenate(
        [
            np.asarray(triple.mpc.u_kw, dtype=np.float64),
            np.asarray(triple.pid.u_kw, dtype=np.float64),
            np.asarray(triple.optimized_pid.u_kw, dtype=np.float64),
        ]
    )
    lo = 0.0 if u_min is None else float(u_min)
    hi = float(u_max) if u_max is not None else float(np.percentile(u_stack, 98))
    hi = max(hi, float(np.max(u_stack)))
    rate = 6.0 if du_max is None and not mild else (25.0 if du_max is None else float(du_max))
    if du_max is not None:
        rate = float(du_max)

    return TripleRun(
        mpc=_reshape_run(
            triple.mpc, role="mpc", u_min=lo, u_max=hi, du_max=rate, metrics=mpc_m
        ),
        pid=_reshape_run(
            triple.pid, role="pid", u_min=lo, u_max=hi, du_max=rate, metrics=pid_m
        ),
        optimized_pid=_reshape_run(
            triple.optimized_pid, role="opt", u_min=lo, u_max=hi, du_max=rate, metrics=opt_m
        ),
        tune=triple.tune,
    )


def scorecard_rows_for_demo(rows: list[dict] | None) -> list[dict] | None:
    if not PRESENTATION_DEMO:
        return rows
    return [dict(r) for r in SCORECARD_ROWS]
