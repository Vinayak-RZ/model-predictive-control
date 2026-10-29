"""Step-through MPC horizon for teaching receding-horizon control."""

from __future__ import annotations

import streamlit as st

from mpc_core.sim.config import default_demo_config
from mpc_core.sim.plotly_charts import mpc_horizon_figure
from mpc_core.sim.scenarios import SCENARIOS
from mpc_core.sim.simulate import run_mpc_step_log
from mpc_core.sim.ui import inject_styles, page_header, sidebar_brand

st.set_page_config(page_title="Step-through · MPC Heater Lab", layout="wide")
inject_styles()
sidebar_brand()

page_header(
    eyebrow="Receding horizon",
    title="Step-through",
    look_for=(
        "At each sample MPC plans a temperature fan over the horizon, then applies "
        "only the first power move. Step forward to see the plan rewrite."
    ),
)

top_l, top_r = st.columns([2, 1])
with top_l:
    scenario_key = st.selectbox(
        "Scenario",
        options=list(SCENARIOS.keys()),
        format_func=lambda k: SCENARIOS[k].title,
    )
with top_r:
    horizon = st.slider("Horizon steps", 5, 35, 25)

cfg = default_demo_config()


@st.cache_data
def load_log(key: str, h: int):
    sc = SCENARIOS[key]
    return run_mpc_step_log(sc, cfg=cfg, horizon_steps=h, max_steps=70)


log = load_log(scenario_key, horizon)

if "mpc_step_idx" not in st.session_state:
    st.session_state.mpc_step_idx = 0

# Reset step when scenario/horizon changes
state_key = f"{scenario_key}:{horizon}"
if st.session_state.get("mpc_step_key") != state_key:
    st.session_state.mpc_step_key = state_key
    st.session_state.mpc_step_idx = 0

idx = st.session_state.mpc_step_idx
idx = max(0, min(idx, len(log.snapshots) - 1))
snap = log.snapshots[idx]

nav1, nav2, nav3 = st.columns([1, 1, 3])
with nav1:
    if st.button("Previous", disabled=idx <= 0, use_container_width=True):
        st.session_state.mpc_step_idx = idx - 1
        st.rerun()
with nav2:
    if st.button(
        "Next",
        type="primary",
        disabled=idx >= len(log.snapshots) - 1,
        use_container_width=True,
    ):
        st.session_state.mpc_step_idx = idx + 1
        st.rerun()
with nav3:
    scrub = st.slider(
        "Step",
        min_value=1,
        max_value=len(log.snapshots),
        value=idx + 1,
        help=f"t = {snap.time_s:.0f} s",
    )
    if scrub - 1 != idx:
        st.session_state.mpc_step_idx = scrub - 1
        st.rerun()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Applied power", f"{snap.u_applied:.2f} kW")
m2.metric("Disturbance d̂", f"{snap.d_hat:.3f}")
m3.metric("Measured / setpoint", f"{snap.y_meas:.1f} / {snap.y_ref:.1f} °C")
m4.metric("Solve time", f"{snap.solve_ms:.2f} ms")

st.plotly_chart(mpc_horizon_figure(snap), use_container_width=True)
st.caption(snap.caption)
