"""Interactive MPC vs PID comparison for industrial control coursework."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="MPC Heater Lab",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("MPC Heater Lab")
st.markdown(
    """
Compare **offset-free MPC**, a **hand-tuned PID**, and an **optimized PID** on the same
heat-balance heater model. Use the pages in the sidebar:

1. **Playground** — sliders, presets, and live traces  
2. **Step-through** — one MPC horizon at a time  
3. **Scorecard** — scenario metrics for all three controllers  

Run locally: `pip install -r requirements.txt && pip install -e . && streamlit run app.py`
"""
)
st.info("Start on **Playground** to explore setpoints, disturbances, and power limits.")
