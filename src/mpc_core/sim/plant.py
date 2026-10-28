"""IBH truth model with optional time-varying disturbances."""

from __future__ import annotations

from dataclasses import dataclass, field

from mpc_core.twin.ibh import IBHParams, step_ibh


@dataclass
class IBHPlantState:
    T_c: float
    params: IBHParams
    events_applied: set[str] = field(default_factory=set)


def apply_disturbance_event(state: IBHPlantState, event: str) -> IBHPlantState:
    """Apply named mid-run disturbance once."""
    if event in state.events_applied:
        return state
    params = state.params
    if event == "ambient_step":
        params = IBHParams(
            m_kg=params.m_kg,
            c_p_j_per_kg_k=params.c_p_j_per_kg_k,
            eta=params.eta,
            U_w_per_k=params.U_w_per_k,
            T_amb_c=params.T_amb_c + 8.0,
        )
    elif event == "heat_loss_bump":
        params = IBHParams(
            m_kg=params.m_kg,
            c_p_j_per_kg_k=params.c_p_j_per_kg_k,
            eta=params.eta,
            U_w_per_k=params.U_w_per_k * 1.45,
            T_amb_c=params.T_amb_c,
        )
    else:
        raise ValueError(f"unknown disturbance event: {event}")
    applied = set(state.events_applied)
    applied.add(event)
    return IBHPlantState(T_c=state.T_c, params=params, events_applied=applied)


def step_plant(state: IBHPlantState, power_kw: float, dt_s: float) -> IBHPlantState:
    p_w = max(0.0, power_kw) * 1000.0
    t_next = step_ibh(
        T_c=state.T_c,
        P_coil_w=p_w,
        dt_s=dt_s,
        params=state.params,
    )
    return IBHPlantState(
        T_c=t_next,
        params=state.params,
        events_applied=state.events_applied,
    )
