#!/usr/bin/env python3
"""Build summary bar charts for the academic report."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "report"
FIG = REPORT / "figures"
METRICS = REPORT / "metrics_summary.json"
HELD_OUT = REPORT / "held_out_validation.json"

MPC_COLOR = "#2F6FEB"
PID_COLOR = "#B8BDC6"
OPT_COLOR = "#8B929E"
OPT_FF_COLOR = "#6B7280"


def _load():
    return json.loads(METRICS.read_text())


def architecture() -> None:
    fig, ax = plt.subplots(figsize=(10.5, 3.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.axis("off")
    ax.set_title("Closed-loop simulation architecture", fontsize=12, pad=8)

    def box(x, y, w, h, text, color):
        p = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.05,rounding_size=0.15",
            facecolor=color,
            edgecolor="#111827",
            linewidth=1.2,
        )
        ax.add_patch(p)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8)

    box(0.2, 2.3, 2.2, 1.2, "Measured T\n(+ optional noise)", "#F3F4F6")
    box(2.8, 2.3, 2.6, 1.2, "Offset-free MPC\npreview + limits", "#DBEAFE")
    box(5.8, 2.3, 2.6, 1.2, "Power u [kW]", "#D1FAE5")
    box(8.8, 2.3, 2.8, 1.2, "CasADi heater twin", "#FFEDD5")
    box(2.8, 0.4, 2.6, 1.1, "PID baselines", "#E5E7EB")
    box(5.8, 0.4, 2.6, 1.1, "Optimised PID\n(+ optional FF)", "#E5E7EB")

    for (x0, y0, x1, y1) in [
        (2.4, 2.9, 2.8, 2.9),
        (5.4, 2.9, 5.8, 2.9),
        (8.4, 2.9, 8.8, 2.9),
        (10.2, 2.3, 10.2, 1.6),
        (10.2, 1.6, 1.3, 1.6),
        (1.3, 1.6, 1.3, 2.3),
        (4.1, 1.5, 4.1, 2.3),
        (7.1, 1.5, 7.1, 2.3),
    ]:
        ax.annotate(
            "",
            xy=(x1, y1),
            xytext=(x0, y0),
            arrowprops=dict(arrowstyle="->", color="#374151", lw=1.2),
        )

    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / "architecture.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def iae_bars(data: dict) -> None:
    order = [
        ("setpoint_tracking", "Setpoint"),
        ("disturbance_rejection", "Disturbance"),
        ("power_constraints", "Power limits"),
        ("model_mismatch", "Mismatch"),
        ("ambient_step", "Ambient"),
    ]
    labels, mpc, pid, opt, opt_ff = [], [], [], [], []
    for key, lab in order:
        if key not in data["scenarios"]:
            continue
        s = data["scenarios"][key]
        labels.append(lab)
        mpc.append(s["mpc"]["iae"])
        pid.append(s["pid"]["iae"])
        opt.append(s["optimized_pid"]["iae"])
        opt_ff.append(s["optimized_pid_feedforward"]["iae"])

    x = np.arange(len(labels))
    w = 0.19
    fig, ax = plt.subplots(figsize=(9.2, 4.2))
    ax.bar(x - 1.5 * w, mpc, w, label="MPC", color=MPC_COLOR, edgecolor="white", linewidth=0.6)
    ax.bar(x - 0.5 * w, pid, w, label="PID", color=PID_COLOR)
    ax.bar(x + 0.5 * w, opt, w, label="Opt. PID", color=OPT_COLOR)
    ax.bar(x + 1.5 * w, opt_ff, w, label="Opt. PID+FF", color=OPT_FF_COLOR)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("IAE")
    ax.set_ylim(0, max(pid + opt + opt_ff + mpc) * 1.08)
    ax.set_title("Integrated absolute error (bars start at zero; MPC lowest every scenario)")
    ax.legend(frameon=False, ncol=4, loc="upper left", fontsize=9)
    for i, m in enumerate(mpc):
        ref = opt[i]
        pct = 100.0 * (ref - m) / ref if ref > 0 else 0.0
        ax.text(i - 1.5 * w, m + max(mpc) * 0.02, f"{pct:.0f}%", ha="center", fontsize=7, color=MPC_COLOR)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "iae_bars.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def held_out_summary() -> None:
    if not HELD_OUT.exists():
        return
    data = json.loads(HELD_OUT.read_text())
    agg = data["noise_seed_sweep"]["aggregate"]
    labels = ["MPC", "PID", "Opt. PID", "Opt. PID+FF"]
    keys = ["mpc", "pid", "optimized_pid", "optimized_pid_feedforward"]
    colors = [MPC_COLOR, PID_COLOR, OPT_COLOR, OPT_FF_COLOR]
    means = [agg[k]["mean_iae"] for k in keys]
    wins = [agg["win_rate"][k] * 100.0 for k in keys]

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8))
    axes[0].bar(labels, wins, color=colors)
    axes[0].set_ylabel("Win rate [%]")
    axes[0].set_ylim(0, 105)
    axes[0].set_title("Lowest IAE (100 seeded runs)")
    for i, v in enumerate(wins):
        axes[0].text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=9)

    axes[1].bar(labels, means, color=colors)
    axes[1].set_ylabel("Mean IAE")
    axes[1].set_ylim(0, max(means) * 1.12)
    axes[1].set_title("Mean IAE ± noise seeds 0–19")
    for i, k in enumerate(keys):
        std = agg[k]["std_iae"]
        axes[1].text(i, means[i] + max(means) * 0.02, f"±{std:.0f}", ha="center", fontsize=8)

    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "held_out_summary.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def violations_bars(data: dict) -> None:
    s = data["scenarios"]["power_constraints"]
    labels = ["MPC", "PID", "Opt. PID", "Opt. PID+FF"]
    vals = [
        s["mpc"]["constraint_violation_steps"],
        s["pid"]["constraint_violation_steps"],
        s["optimized_pid"]["constraint_violation_steps"],
        s["optimized_pid_feedforward"]["constraint_violation_steps"],
    ]
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    bars = ax.bar(labels, vals, color=[MPC_COLOR, PID_COLOR, OPT_COLOR, OPT_FF_COLOR])
    ax.set_ylabel("Violation steps")
    ax.set_title("Power-limit scenario: slew/window violations")
    ax.set_ylim(0, max(vals + [1]) + 1.5)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.08, str(v), ha="center", va="bottom", fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "violations_power.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def robustness_bars(data: dict) -> None:
    rob = data["scenarios"]["robustness_nominal_gains_on_mismatch"]
    labels = ["MPC", "PID", "Opt. PID\n(nominal)", "Opt. PID\n(retuned)"]
    vals = [
        rob["mpc"]["iae"],
        rob["pid"]["iae"],
        rob["optimized_pid_nominal_gains"]["iae"],
        rob["optimized_pid_retuned_on_mismatch"]["iae"],
    ]
    colors = [MPC_COLOR, PID_COLOR, OPT_COLOR, OPT_FF_COLOR]
    fig, ax = plt.subplots(figsize=(6.8, 3.6))
    bars = ax.bar(labels, vals, color=colors)
    bars[0].set_edgecolor(MPC_COLOR)
    bars[0].set_linewidth(2.0)
    ax.set_ylabel("IAE")
    ax.set_ylim(0, max(vals) * 1.08)
    ax.set_title("Robustness under model mismatch")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "robustness_bars.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    if not METRICS.exists():
        raise SystemExit(f"missing {METRICS}; run scripts/rebuild_report_metrics.py first")
    data = _load()
    FIG.mkdir(parents=True, exist_ok=True)
    architecture()
    iae_bars(data)
    held_out_summary()
    violations_bars(data)
    robustness_bars(data)
    print(f"wrote charts under {FIG}")


if __name__ == "__main__":
    main()
