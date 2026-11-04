"""Measured slow-varying plant parameters for MPC feedforward (course demo).

When ambient temperature or effective heat-loss coefficient are measured on the
plant, the controller can add a steady-state power correction before the
offset-free disturbance state absorbs the remainder. See docs/mpc_literature.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from mpc_core.twin.ibh import IBHParams


@dataclass(frozen=True)
class MeasuredPlantContext:
    """Disturbance-related parameters available to every controller in the sim."""

    T_amb_c: float
    U_w_per_k: float

    @classmethod
    def from_ibh_params(cls, params: IBHParams) -> MeasuredPlantContext:
        return cls(T_amb_c=params.T_amb_c, U_w_per_k=params.U_w_per_k)


def steady_state_loss_offset_kw(
    *,
    y_c: float,
    nominal: IBHParams,
    measured: MeasuredPlantContext,
) -> float:
    """Extra coil power (kW) to offset change in U·(T − T_amb) at temperature y_c.

    Derived from the heater heat balance at fixed y: η·ΔP ≈ Δ(U·(T − T_amb)).
    """
    loss_nom_w = nominal.U_w_per_k * (y_c - nominal.T_amb_c)
    loss_meas_w = measured.U_w_per_k * (y_c - measured.T_amb_c)
    delta_w = loss_meas_w - loss_nom_w
    return delta_w / (nominal.eta * 1000.0)


def kalman_disturbance_observer_gain(
    model_a: float,
    *,
    disturbance_process_var: float = 0.35,
    measurement_var: float = 0.12,
) -> float:
    """Scalar innovation gain for an integrating output disturbance (bias) model.

    Matches a random-walk disturbance with variance ``disturbance_process_var`` and
    measurement noise ``measurement_var`` on a plant with pole ``model_a``. Tuned
    for the illustrative ARX in ``default_demo_config()``; retune if the fit moves.
    """
    if not 0.0 < model_a < 1.0:
        raise ValueError("model_a must be in (0, 1)")
    if disturbance_process_var <= 0.0 or measurement_var <= 0.0:
        raise ValueError("variances must be positive")
    # Steady-state Kalman gain for bias-on-output with AR(1) plant (see mpc_literature.md).
    one_minus_a = 1.0 - model_a
    q = disturbance_process_var
    r = measurement_var
    # Positive root of L^2 + (r + (1-a)^2 q/(1-a)) L - q = 0 simplified for demo pole.
    disc = (r + one_minus_a * q) ** 2 + 4.0 * q * one_minus_a
    gain = (-(r + one_minus_a * q) + (disc**0.5)) / (2.0 * one_minus_a)
    return float(max(1.0, min(gain, 4.0)))
