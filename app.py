"""MPC Heater Lab — Streamlit entry (st.navigation)."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="MPC Heater Lab",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded",
)

overview = st.Page("ui_pages/overview.py", title="Overview", default=True)
playground = st.Page("ui_pages/playground.py", title="Playground")
step_through = st.Page("ui_pages/step_through.py", title="Step-through")
scorecard = st.Page("ui_pages/scorecard.py", title="Scorecard")

pg = st.navigation([overview, playground, step_through, scorecard])
pg.run()
