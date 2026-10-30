"""Illustrative simulation parameters (course demo, not plant/customer data)."""

from __future__ import annotations

from dataclasses import dataclass

from mpc_core import IdentifiedLinearModel, SetpointLimits
from mpc_core.twin.ibh import IBHParams


@dataclass(frozen=True)
class DemoConfig:
    """Shared knobs for batch runs and the Streamlit app."""

    ibh: IBHParams
    model: IdentifiedLinearModel
    limits: SetpointLimits
    dt_s: float
    horizon_steps: int
    solver_time_limit_s: float
    setpoint_id: str = "power_setpoint"
    control_horizon: int = 1
    move_weight: float = 0.0
    terminal_weight: float = 0.0
    observer_gain: float = 1.0
    tracking_weight: float = 1.0


def default_demo_config() -> DemoConfig:
    """Heater fixture scaled for a slow thermal response; ARX fitted offline.

    Retuned MPC defaults (coursework, box experiments 31 Oct 2026):
    prediction horizon 40, control horizon 1 (held move), terminal weight 50,
    reference preview enabled in the simulator, observer gain 1.0.
    Same plant and ARX as before. Multi-move trials raised IAE on this heater.
    """
    ibh = IBHParams(
        m_kg=800.0,
        c_p_j_per_kg_k=480.0,
        eta=0.82,
        U_w_per_k=45.0,
        T_amb_c=25.0,
    )
    # Fitted from a 120 s power step on the heater twin (least squares, illustrative).
    model = IdentifiedLinearModel(
        fit_id="fit-ibh-illustrative",
        a=0.978,
        b=0.042,
        dt_s=1.0,
        n_samples=120,
        residual_rms=0.35,
        experiment="ibh_step_fit",
    )
    limits = SetpointLimits("power_setpoint", "kW", 0.0, 250.0, 25.0)
    return DemoConfig(
        ibh=ibh,
        model=model,
        limits=limits,
        dt_s=1.0,
        horizon_steps=40,
        solver_time_limit_s=2.0,
        control_horizon=1,
        move_weight=0.0,
        terminal_weight=50.0,
        observer_gain=1.0,
        tracking_weight=1.0,
    )
