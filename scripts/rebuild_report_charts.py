#!/usr/bin/env python3
"""Build architecture and summary bar charts for the academic report.

Reads ``report/metrics_summary.json`` (run ``scripts/rebuild_report_metrics.py``
first) and writes PNGs under ``report/figures/``.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "report"
FIG = REPORT / "figures"
METRICS = REPORT / "metrics_summary.json"


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
            (x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.15",
            facecolor=color, edgecolor="#111827", linewidth=1.2,
        )
        ax.add_patch(p)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=8, wrap=True)

    box(0.2, 2.3, 2.2, 1.2, "Measured T\n(+ optional noise)", "#F3F4F6")
    box(2.8, 2.3, 2.6, 1.2, "Offset-free MPC\nARX + d update,\nL-BFGS-B, preview + limits", "#DBEAFE")
    box(5.8, 2.3, 2.6, 1.2, "Power u [kW]\nclipped to\nwindow + rate", "#D1FAE5")
    box(8.8, 2.3, 2.8, 1.2, "CasADi heater twin\nm cp dT/dt", "#FFEDD5")
    box(2.8, 0.4, 2.6, 1.1, "Hand-tuned PID\n(anti-windup)", "#E5E7EB")
    box(5.8, 0.4, 2.6, 1.1, "Optimized PID\nIAE + viol. penalty\nSciPy L-BFGS-B", "#CCFBF1")

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
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="->", color="#374151", lw=1.2))

    FIG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
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
    labels, mpc, pid, opt = [], [], [], []
    for key, lab in order:
        if key not in data["scenarios"]:
            continue
        s = data["scenarios"][key]
        labels.append(lab)
        mpc.append(s["mpc"]["iae"])
        pid.append(s["pid"]["iae"])
        opt.append(s["optimized_pid"]["iae"])

    import numpy as np
    x = np.arange(len(labels))
    w = 0.25
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    b1 = ax.bar(x - w, mpc, w, label="MPC", color="#2563EB")
    ax.bar(x, pid, w, label="PID", color="#6B7280")
    ax.bar(x + w, opt, w, label="Opt. PID", color="#0D9488")
    for i, (m, o) in enumerate(zip(mpc, opt)):
        if m <= o and m <= pid[i]:
            b1[i].set_hatch("//")
            b1[i].set_edgecolor("white")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("IAE")
    ax.set_title("Integrated absolute error by scenario (hatched = MPC best)")
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "iae_bars.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def violations_bars(data: dict) -> None:
    s = data["scenarios"]["power_constraints"]
    vals = [
        s["mpc"]["constraint_violation_steps"],
        s["pid"]["constraint_violation_steps"],
        s["optimized_pid"]["constraint_violation_steps"],
    ]
    fig, ax = plt.subplots(figsize=(4.5, 3.2))
    bars = ax.bar(["MPC", "PID", "Opt. PID"], vals,
                  color=["#2563EB", "#6B7280", "#0D9488"])
    ax.set_ylabel("Violation steps")
    ax.set_title("Power-limit scenario: slew/window violations")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.1, str(v),
                ha="center", va="bottom", fontsize=10)
    ax.set_ylim(0, max(vals + [1]) + 1.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "violations_power.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


def robustness_bars(data: dict) -> None:
    rob = data["scenarios"]["robustness_nominal_gains_on_mismatch"]
    labels = ["MPC", "PID", "Opt. PID\n(nominal gains)", "Opt. PID\n(retuned on mismatch)"]
    vals = [
        rob["mpc"]["iae"],
        rob["pid"]["iae"],
        rob["optimized_pid_nominal_gains"]["iae"],
        rob["optimized_pid_retuned_on_mismatch"]["iae"],
    ]
    colors = ["#2563EB", "#6B7280", "#0D9488", "#5EEAD4"]
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    bars = ax.bar(labels, vals, color=colors)
    bars[0].set_hatch("//")
    bars[0].set_edgecolor("white")
    ax.set_ylabel("IAE")
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
    violations_bars(data)
    robustness_bars(data)
    print(f"wrote charts under {FIG}")


if __name__ == "__main__":
    main()
