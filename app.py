"""Interactive MPC vs PID comparison for industrial control coursework."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from mpc_core.sim.ui import (
    demo_path,
    footer_note,
    inject_styles,
    page_header,
    sidebar_brand,
    takeaway,
)

st.set_page_config(
    page_title="MPC Heater Lab",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()
sidebar_brand()

logo = Path(__file__).parent / "assets" / "mpc-heater-lab-logo.svg"
cols = st.columns([1, 8])
with cols[0]:
    if logo.exists():
        st.image(str(logo), width=64)

page_header(
    eyebrow="Professor demo",
    title="MPC Heater Lab",
    look_for=(
        "Same heat-balance plant, three controllers: offset-free MPC, hand-tuned PID, "
        "and SciPy-optimized PID. The demo shows where planning beats reaction, "
        "especially under tight power and rate limits."
    ),
)

takeaway(
    label="What this project shows",
    body=(
        "MPC stays feasible on power limits (zero violation steps) while plain PID "
        "breaks the slew rule. Optimized PID can match tracking after retuning, but "
        "still cannot preview a future setpoint the way MPC does."
    ),
)

st.markdown("##### Live walkthrough (about 5 minutes)")
demo_path(
    [
        (
            "Step 1 · Live",
            "Playground",
            "Open the Tight power limit preset. Point at the power subplot: MPC "
            "ramps inside the dashed bounds; PID saturates and violates the rate limit.",
        ),
        (
            "Step 2 · Mechanism",
            "Step-through",
            "Advance a few samples. Show the predicted temperature fan and that only "
            "the first power move is applied each step (receding horizon).",
        ),
        (
            "Step 3 · Proof",
            "Scorecard",
            "Start with the power-limits takeaway (violations), then IAE and settling. "
            "Call out the model-mismatch row so the comparison stays honest.",
        ),
    ]
)

st.info("Start on **Playground** in the sidebar. Use presets so you are not tuning live.")

footer_note(
    "Educational simulation lab · not a field PLC program"
)
