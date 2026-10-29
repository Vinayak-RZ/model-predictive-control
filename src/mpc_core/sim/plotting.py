"""Matplotlib figures for MPC vs PID (layout inspired by public MPC tutorials)."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from mpc_core.sim.metrics import SimulationMetrics
from mpc_core.sim.simulate import SimulationResult


def apply_plot_style() -> None:
    """Readable defaults (grid/typography similar to do-mpc getting-started docs)."""
    mpl.rcParams.update(
        {
            "axes.grid": True,
            "font.size": 11,
            "lines.linewidth": 2.0,
            "figure.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def save_triple_figure(
    *,
    title: str,
    mpc: SimulationResult,
    pid: SimulationResult,
    optimized_pid: SimulationResult,
    path: Path,
) -> None:
    apply_plot_style()
    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(10, 6.5), constrained_layout=True)
    axes[0].plot(mpc.time_s, mpc.y_ref, "k--", label="Setpoint", alpha=0.7)
    axes[0].plot(mpc.time_s, mpc.y_c, label="MPC", color="#2563eb")
    axes[0].plot(pid.time_s, pid.y_c, label="PID", color="#71717a")
    axes[0].plot(optimized_pid.time_s, optimized_pid.y_c, label="Opt. PID", color="#0d9488")
    axes[0].set_ylabel("Temperature [°C]")
    axes[0].legend(loc="best")
    axes[0].set_title(title)

    axes[1].plot(mpc.time_s, mpc.u_kw, label="MPC", color="#2563eb")
    axes[1].plot(pid.time_s, pid.u_kw, label="PID", color="#71717a")
    axes[1].plot(optimized_pid.time_s, optimized_pid.u_kw, label="Opt. PID", color="#0d9488")
    axes[1].set_ylabel("Coil power [kW]")
    axes[1].set_xlabel("Time [s]")
    axes[1].legend(loc="best")

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def save_comparison_figure(
    *,
    title: str,
    mpc: SimulationResult,
    pid: SimulationResult,
    path: Path,
) -> None:
    apply_plot_style()
    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(10, 8), constrained_layout=True)

    axes[0].plot(mpc.time_s, mpc.y_ref, "k--", label="Setpoint", alpha=0.7)
    axes[0].plot(mpc.time_s, mpc.y_c, label="MPC")
    axes[0].plot(pid.time_s, pid.y_c, label="PID", alpha=0.85)
    axes[0].set_ylabel("Temperature [°C]")
    axes[0].legend(loc="best")
    axes[0].set_title(title)

    axes[1].plot(mpc.time_s, mpc.u_kw, label="MPC power")
    axes[1].plot(pid.time_s, pid.u_kw, label="PID power", alpha=0.85)
    axes[1].set_ylabel("Coil power [kW]")

    if mpc.d_hat is not None:
        axes[2].plot(mpc.time_s, mpc.d_hat, color="#2a6f97", label="MPC d_hat")
    axes[2].set_ylabel("Disturbance est.")
    axes[2].set_xlabel("Time [s]")
    axes[2].legend(loc="best")

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def format_metrics_table(mpc_m: SimulationMetrics, pid_m: SimulationMetrics) -> str:
    def row(name: str, a: float | None, b: float | None) -> str:
        sa = "—" if a is None else f"{a:.3g}"
        sb = "—" if b is None else f"{b:.3g}"
        return f"| {name} | {sa} | {sb} |"

    lines = [
        "| Metric | MPC | PID |",
        "| --- | --- | --- |",
        row("IAE", mpc_m.iae, pid_m.iae),
        row("ISE", mpc_m.ise, pid_m.ise),
        row("Overshoot [%]", mpc_m.overshoot_pct, pid_m.overshoot_pct),
        row("Settling time [s]", mpc_m.settling_time_s, pid_m.settling_time_s),
        row("Constraint violation steps", float(mpc_m.constraint_violation_steps), float(pid_m.constraint_violation_steps)),
        row("Energy [kWh]", mpc_m.energy_kwh, pid_m.energy_kwh),
    ]
    return "\n".join(lines)
