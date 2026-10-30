"""Overview landing page."""

from __future__ import annotations

from pathlib import Path

import path_setup  # noqa: F401
import streamlit as st

from mpc_core.sim.copy_text import (
    OVERVIEW_LEDE,
    OVERVIEW_MPC_BLURB,
    OVERVIEW_PAGES,
    OVERVIEW_TITLE,
)
from mpc_core.sim.ui import inject_styles, page_header

inject_styles()

page_header(title=OVERVIEW_TITLE, look_for=OVERVIEW_LEDE)

diagram = Path(__file__).resolve().parents[1] / "assets" / "mpc-infographic.png"
if diagram.exists():
    st.image(str(diagram), use_container_width=True)

st.markdown(OVERVIEW_MPC_BLURB)

st.markdown("")
for name, line in OVERVIEW_PAGES:
    st.markdown(
        f'<div class="lab-path-item">'
        f'<p class="lab-path-title">{name}</p>'
        f'<p class="lab-path-body">{line}</p></div>',
        unsafe_allow_html=True,
    )
