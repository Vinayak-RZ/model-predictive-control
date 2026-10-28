"""CasADi induction billet heater (IBH) heat-balance twin (W3.7).

Structure follows the research heat-balance form (lumped billet temperature):

    m * c_p * dT/dt = eta * P_coil - U * (T - T_amb)

No physical number is baked in. Every coefficient is a named parameter that
must be status=set before a step runs. Plant geometry (coil slot count, coil
frequency, billet diameter) is not invented here; it stays for pack binding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import casadi as ca  # type: ignore[import-untyped]


class OpenTwinParameter(Exception):
    """Raised when a twin step needs a parameter that is still open."""

    def __init__(self, names: list[str]) -> None:
        self.names = names
        super().__init__("open twin parameter: " + ", ".join(names))


# Names match the generated C ABI in twin-runtime/generated/ibh_step.c
IBH_PARAM_NAMES: tuple[str, ...] = (
    "m_kg",
    "c_p_j_per_kg_k",
    "eta",
    "U_w_per_k",
    "T_amb_c",
)


@dataclass(frozen=True)
class IBHParams:
    """Physical coefficients for one IBH heat-balance step. All must be set."""

    m_kg: float
    c_p_j_per_kg_k: float
    eta: float
    U_w_per_k: float
    T_amb_c: float

    def as_vector(self) -> list[float]:
        return [
            self.m_kg,
            self.c_p_j_per_kg_k,
            self.eta,
            self.U_w_per_k,
            self.T_amb_c,
        ]


def require_params(raw: Mapping[str, float | None]) -> IBHParams:
    """Build IBHParams or raise with every missing/open name (no defaults)."""
    opened: list[str] = []
    vals: dict[str, float] = {}
    for name in IBH_PARAM_NAMES:
        v = raw.get(name)
        if v is None:
            opened.append(name)
        else:
            vals[name] = float(v)
    if opened:
        raise OpenTwinParameter(opened)
    return IBHParams(
        m_kg=vals["m_kg"],
        c_p_j_per_kg_k=vals["c_p_j_per_kg_k"],
        eta=vals["eta"],
        U_w_per_k=vals["U_w_per_k"],
        T_amb_c=vals["T_amb_c"],
    )


def ibh_step_function() -> ca.Function:
    """CasADi Function: (T_c, P_coil_w, dt_s, params[5]) -> T_next_c.

    Explicit Euler on the heat balance. Same signature as the generated C.
    """
    T = ca.SX.sym("T_c")
    P = ca.SX.sym("P_coil_w")
    dt = ca.SX.sym("dt_s")
    p = ca.SX.sym("p", len(IBH_PARAM_NAMES))
    m, c_p, eta, U, T_amb = p[0], p[1], p[2], p[3], p[4]
    dT = (eta * P - U * (T - T_amb)) / (m * c_p)
    T_next = T + dt * dT
    return ca.Function(
        "ibh_step",
        [T, P, dt, p],
        [T_next],
        ["T_c", "P_coil_w", "dt_s", "p"],
        ["T_next_c"],
    )


def step_ibh(
    *,
    T_c: float,
    P_coil_w: float,
    dt_s: float,
    params: IBHParams,
) -> float:
    """One recommend-side twin step in Python (parity with generated C)."""
    if dt_s <= 0:
        raise ValueError("dt_s must be positive")
    if params.m_kg <= 0 or params.c_p_j_per_kg_k <= 0:
        raise ValueError("m_kg and c_p_j_per_kg_k must be positive")
    fn = ibh_step_function()
    out = fn(T_c, P_coil_w, dt_s, params.as_vector())
    return float(out)  # type: ignore[arg-type]
