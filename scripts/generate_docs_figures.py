#!/usr/bin/env python3
"""Render README/docs PNGs from real batch simulation outputs."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from mpc_core.sim.pid_tune import tune_pid_gains
from mpc_core.sim.plotting import save_scenario_figure, save_triple_figure
from mpc_core.sim.scenarios import SCENARIOS
from mpc_core.sim.simulate import RunOptions, run_closed_loop


def _make_cfg_and_mpc():
    from dataclasses import replace
    from mpc_core.sim.config import default_demo_config

    cfg = default_demo_config()
    cfg = replace(
        cfg,
        horizon_steps=40,
        control_horizon=1,
        move_weight=0.0,
        terminal_weight=50.0,
        observer_gain=cfg.observer_gain,
        tracking_weight=1.0,
        solver_time_limit_s=2.0,
    )

    def run_mpc(scenario, cfg, options=None):
        return run_closed_loop(
            scenario,
            "mpc",
            cfg=cfg,
            options=options or RunOptions(),
            mpc_tracking_weight=cfg.tracking_weight,
            mpc_control_horizon=cfg.control_horizon,
            mpc_move_weight=cfg.move_weight,
            mpc_terminal_weight=cfg.terminal_weight,
            mpc_observer_gain=cfg.observer_gain,
            mpc_preview=True,
        )

    return cfg, run_mpc

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REPORT_FIG = ROOT / "report" / "figures"
METRICS = ROOT / "report" / "metrics_summary.json"


def _comparison_png() -> None:
    cfg, run_mpc = _make_cfg_and_mpc()
    sc = SCENARIOS["setpoint_tracking"]
    tune = tune_pid_gains(sc, cfg=cfg, maxiter=30)
    tune_ff = tune_pid_gains(sc, cfg=cfg, maxiter=30, pid_measured_feedforward=True)
    mpc = run_mpc(sc, cfg)
    pid = run_closed_loop(sc, "pid", cfg=cfg)
    opt = run_closed_loop(sc, "pid", cfg=cfg, pid_gains=tune.gains)
    opt_ff = run_closed_loop(
        sc,
        "pid",
        cfg=cfg,
        pid_gains=tune_ff.gains,
        pid_measured_feedforward=True,
    )
    out = DOCS / "streamlit-comparison-plots.png"
    save_scenario_figure(
        title="Setpoint tracking — batch simulation traces",
        mpc=mpc,
        pid=pid,
        optimized_pid=opt,
        optimized_pid_ff=opt_ff,
        path=out,
    )
    shutil.copy2(out, REPORT_FIG / "streamlit-comparison-plots.png")


def _metrics_table_png() -> None:
    data = json.loads(METRICS.read_text())["scenarios"]
    rows = []
    for key in (
        "setpoint_tracking",
        "disturbance_rejection",
        "power_constraints",
        "model_mismatch",
        "ambient_step",
    ):
        s = data[key]
        rows.append(
            (
                key.replace("_", " ").title()[:14],
                s["mpc"]["iae"],
                s["optimized_pid"]["iae"],
                s["optimized_pid_feedforward"]["iae"],
            )
        )
    labels = [r[0] for r in rows]
    mpc_vals = [r[1] for r in rows]
    opt_vals = [r[2] for r in rows]
    x = np.arange(len(labels))
    w = 0.25
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.bar(x - w / 2, mpc_vals, w, label="MPC", color="#2F6FEB")
    ax.bar(x + w / 2, opt_vals, w, label="Opt. PID", color="#8B929E")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("IAE")
    ax.set_ylim(0, max(mpc_vals + opt_vals) * 1.1)
    ax.set_title("Scorecard IAE — MPC vs optimised PID (real batch metrics)")
    ax.legend(frameon=False)
    fig.tight_layout()
    out = DOCS / "streamlit-metrics-table.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    plt.close(fig)
    shutil.copy2(out, REPORT_FIG / "streamlit-metrics-table.png")


def _poster_from_power() -> None:
    src = REPORT_FIG / "power_constraints.png"
    if src.exists():
        shutil.copy2(src, DOCS / "video-poster.png")
        shutil.copy2(src, REPORT_FIG / "video-poster.png")


def _sync_docs_from_report_figures() -> None:
    """Map batch scenario PNGs to README Streamlit screenshot slots."""
    mapping = {
        "streamlit-playground-setpoint.png": "setpoint_tracking.png",
        "streamlit-playground-cold-door.png": "ambient_step.png",
        "streamlit-playground-heat-loss-noise.png": "disturbance_rejection.png",
        "streamlit-playground-tight-power.png": "power_constraints.png",
        "streamlit-playground-mismatch.png": "model_mismatch.png",
        "streamlit-playground.png": "power_constraints.png",
        "streamlit-playground-soft-limits.png": "setpoint_tracking.png",
        "streamlit-step-through.png": "setpoint_tracking.png",
    }
    for doc_name, fig_name in mapping.items():
        src = REPORT_FIG / fig_name
        if src.exists():
            shutil.copy2(src, DOCS / doc_name)
            shutil.copy2(src, REPORT_FIG / doc_name)
    held = REPORT_FIG / "held_out_summary.png"
    if held.exists():
        shutil.copy2(held, DOCS / "streamlit-scorecard.png")
        shutil.copy2(held, REPORT_FIG / "streamlit-scorecard.png")
    preview = REPORT_FIG / "power_constraints.png"
    if preview.exists():
        shutil.copy2(preview, REPORT_FIG / "demo-preview-frame.png")
        shutil.copy2(preview, DOCS / "demo-preview-frame.png")
    arch = REPORT_FIG / "architecture.png"
    if arch.exists():
        shutil.copy2(arch, DOCS / "streamlit-overview.png")
        shutil.copy2(arch, REPORT_FIG / "streamlit-overview.png")
    vid_assets = ROOT / "video" / "assets"
    vid_assets.mkdir(parents=True, exist_ok=True)
    if preview.exists():
        shutil.copy2(preview, vid_assets / "ui-playground.png")
    if held.exists():
        shutil.copy2(held, vid_assets / "ui-scorecard.png")


def _demo_gif() -> None:
    """Short GIF preview from the power-limit figure (static loop)."""
    try:
        from PIL import Image
    except ImportError:
        return
    src = DOCS / "video-poster.png"
    if not src.exists():
        return
    im = Image.open(src)
    gif_path = DOCS / "demo-preview.gif"
    im.save(gif_path, save_all=True, append_images=[im], duration=800, loop=0)


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    REPORT_FIG.mkdir(parents=True, exist_ok=True)
    _comparison_png()
    _metrics_table_png()
    _poster_from_power()
    _sync_docs_from_report_figures()
    _demo_gif()
    print("Wrote docs marketing PNGs from simulation data")


if __name__ == "__main__":
    main()
