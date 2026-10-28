"""Offset-free MPC and CasADi heat-balance heater twin for coursework simulations.

MPC quadratic programme: SciPy L-BFGS-B (see mpc.py).
Plant twin authoring: CasADi (see twin/ibh.py).
"""

from mpc_core.identified import IdentifiedLinearModel
from mpc_core.model_card import HeldOutMetrics, ModelCard
from mpc_core.mpc import MpcResult, MpcState, MpcTimedOut, refresh_disturbance, solve
from mpc_core.thresholds import SetpointLimits

__all__ = [
    "HeldOutMetrics",
    "IdentifiedLinearModel",
    "ModelCard",
    "MpcResult",
    "MpcState",
    "MpcTimedOut",
    "SetpointLimits",
    "refresh_disturbance",
    "solve",
]
