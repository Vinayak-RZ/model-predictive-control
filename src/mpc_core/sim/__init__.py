"""Closed-loop simulations: IBH plant, PID baseline, MPC comparison."""

from mpc_core.sim.metrics import SimulationMetrics, compute_metrics
from mpc_core.sim.scenarios import SCENARIOS, ScenarioConfig
from mpc_core.sim.simulate import SimulationResult, run_closed_loop

__all__ = [
    "SCENARIOS",
    "ScenarioConfig",
    "SimulationMetrics",
    "SimulationResult",
    "compute_metrics",
    "run_closed_loop",
]
