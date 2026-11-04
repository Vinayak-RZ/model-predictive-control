"""Matplotlib figures for MPC vs PID comparisons (shared repo chart style)."""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset

from mpc_core.sim.metrics import SimulationMetrics
from mpc_core.sim.simulate import SimulationResult

# Match Streamlit cobalt accent; PIDs stay muted grey everywhere.
MPC_COLOR = "#2F6FEB"
PID_COLOR = "#B8BDC6"
OPT_PID_COLOR = "#8B929E"
OPT_PID_FF_COLOR = "#6B7280"
SETPOINT_COLOR = "#374151"

LW_MPC = 3.2
LW_OTHER = 1.6
Z_MPC = 5
Z_OTHER = 2


def apply_plot_style() -> None:
    mpl.rcParams.update(
        {
            "axes.grid": True,
            "grid.alpha": 0.35,
            "font.size": 11,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def _pct_improvement(mpc_iae: float, ref_iae: float) -> float:
    if ref_iae <= 0:
        return 0.0
    return 100.0 * (ref_iae - mpc_iae) / ref_iae


def _annotation_text(mpc_m: SimulationMetrics, ref_m: SimulationMetrics) -> str:
    pct = _pct_improvement(mpc_m.iae, ref_m.iae)
    sign = "+" if pct >= 0 else ""
    return (
        f"MPC IAE = {mpc_m.iae:.0f}\n"
        f"{sign}{pct:.1f}% vs opt. PID"
    )


def _plot_trace_stack(
    ax: plt.Axes,
    time_s: np.ndarray,
    *,
    y_ref: np.ndarray | None = None,
    pid: SimulationResult | None = None,
    opt: SimulationResult | None = None,
    opt_ff: SimulationResult | None = None,
    mpc: SimulationResult,
    ylabel: str,
    show_legend: bool = True,
) -> None:
    if y_ref is not None:
        ax.plot(time_s, y_ref, "--", color=SETPOINT_COLOR, lw=1.2, alpha=0.65, label="Setpoint", zorder=1)
    if pid is not None:
        ax.plot(
            pid.time_s,
            pid.y_c if ylabel.startswith("Temp") else pid.u_kw,
            color=PID_COLOR,
            lw=LW_OTHER,
            label="PID",
            zorder=Z_OTHER,
        )
    if opt is not None:
        ax.plot(
            opt.time_s,
            opt.y_c if ylabel.startswith("Temp") else opt.u_kw,
            color=OPT_PID_COLOR,
            lw=LW_OTHER,
            label="Opt. PID",
            zorder=Z_OTHER + 1,
        )
    if opt_ff is not None:
        ax.plot(
            opt_ff.time_s,
            opt_ff.y_c if ylabel.startswith("Temp") else opt_ff.u_kw,
            color=OPT_PID_FF_COLOR,
            lw=LW_OTHER,
            ls="-.",
            label="Opt. PID+FF",
            zorder=Z_OTHER + 2,
        )
    series = mpc.y_c if ylabel.startswith("Temp") else mpc.u_kw
    ax.plot(mpc.time_s, series, color=MPC_COLOR, lw=LW_MPC, label="MPC", zorder=Z_MPC)
    ax.set_ylabel(ylabel)
    if show_legend:
        ax.legend(loc="best", frameon=True, fontsize=9)


def save_scenario_figure(
    *,
    title: str,
    mpc: SimulationResult,
    pid: SimulationResult,
    optimized_pid: SimulationResult,
    path: Path,
    optimized_pid_ff: SimulationResult | None = None,
    zoom_time: tuple[float, float] | None = None,
    zoom_temp: tuple[float, float] | None = None,
    iae_reference: SimulationResult | None = None,
) -> None:
    """Save temperature + power figure with MPC emphasised and IAE callout."""
    apply_plot_style()
    ref = iae_reference or optimized_pid
    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(10.5, 7.2), constrained_layout=True)
    fig.suptitle(title, fontsize=13, fontweight="semibold", y=1.02)

    _plot_trace_stack(
        axes[0],
        mpc.time_s,
        y_ref=mpc.y_ref,
        pid=pid,
        opt=optimized_pid,
        opt_ff=optimized_pid_ff,
        mpc=mpc,
        ylabel="Temperature [°C]",
    )
    _plot_trace_stack(
        axes[1],
        mpc.time_s,
        pid=pid,
        opt=optimized_pid,
        opt_ff=optimized_pid_ff,
        mpc=mpc,
        ylabel="Coil power [kW]",
        show_legend=False,
    )
    axes[1].set_xlabel("Time [s]")

    axes[0].text(
        0.02,
        0.97,
        _annotation_text(mpc.metrics, ref.metrics),
        transform=axes[0].transAxes,
        va="top",
        ha="left",
        fontsize=10,
        bbox=dict(boxstyle="round,pad=0.45", facecolor="#EEF3FE", edgecolor=MPC_COLOR, alpha=0.95),
    )

    if zoom_time and zoom_temp:
        t0, t1 = zoom_time
        y0, y1 = zoom_temp
        axins = inset_axes(axes[0], width="38%", height="42%", loc="lower right", borderpad=1.2)
        for run, color, lw, ls in (
            (pid, PID_COLOR, LW_OTHER, "-"),
            (optimized_pid, OPT_PID_COLOR, LW_OTHER, "-"),
            (optimized_pid_ff, OPT_PID_FF_COLOR, LW_OTHER, "-."),
            (mpc, MPC_COLOR, LW_MPC, "-"),
        ):
            if run is None:
                continue
            axins.plot(run.time_s, run.y_c, color=color, lw=lw, ls=ls)
        axins.set_xlim(t0, t1)
        axins.set_ylim(y0, y1)
        axins.set_title("Zoom", fontsize=8)
        axins.tick_params(labelsize=7)
        mark_inset(axes[0], axins, loc1=2, loc2=4, fc="none", ec="#9CA3AF", lw=0.8)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def save_triple_figure(
    *,
    title: str,
    mpc: SimulationResult,
    pid: SimulationResult,
    optimized_pid: SimulationResult,
    path: Path,
    optimized_pid_ff: SimulationResult | None = None,
    scenario_key: str | None = None,
) -> None:
    zoom_time = zoom_temp = None
    if scenario_key == "power_constraints":
        zoom_time = (12.0, 55.0)
        zoom_temp = (84.0, 122.0)
    save_scenario_figure(
        title=title,
        mpc=mpc,
        pid=pid,
        optimized_pid=optimized_pid,
        optimized_pid_ff=optimized_pid_ff,
        path=path,
        zoom_time=zoom_time,
        zoom_temp=zoom_temp,
    )


def save_comparison_figure(
    *,
    title: str,
    mpc: SimulationResult,
    pid: SimulationResult,
    path: Path,
) -> None:
    save_scenario_figure(
        title=title,
        mpc=mpc,
        pid=pid,
        optimized_pid=pid,
        path=path,
    )


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
        row(
            "Constraint violation steps",
            float(mpc_m.constraint_violation_steps),
            float(pid_m.constraint_violation_steps),
        ),
        row("Energy [kWh]", mpc_m.energy_kwh, pid_m.energy_kwh),
    ]
    return "\n".join(lines)
