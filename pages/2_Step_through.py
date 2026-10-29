"""Step-through MPC horizon for teaching receding-horizon control."""

from __future__ import annotations

import streamlit as st

from mpc_core.sim.config import default_demo_config
from mpc_core.sim.plotly_charts import mpc_horizon_figure
from mpc_core.sim.scenarios import SCENARIOS
from mpc_core.sim.simulate import run_mpc_step_log

st.set_page_config(page_title="Step-through MPC", layout="wide")

st.markdown(
    "**This screen** walks through MPC one sample at a time: predicted temperature "
    "over the horizon, then only the first power move is applied."
)

scenario_key = st.selectbox(
    "Scenario",
    options=list(SCENARIOS.keys()),
    format_func=lambda k: SCENARIOS[k].title,
)
horizon = st.slider("Horizon steps", 5, 35, 25)

cfg = default_demo_config()
scenario = SCENARIOS[scenario_key]


@st.cache_data
def load_log(key: str, h: int):
    sc = SCENARIOS[key]
    return run_mpc_step_log(sc, cfg=cfg, horizon_steps=h, max_steps=70)


log = load_log(scenario_key, horizon)

if "mpc_step_idx" not in st.session_state:
    st.session_state.mpc_step_idx = 0

idx = st.session_state.mpc_step_idx
idx = max(0, min(idx, len(log.snapshots) - 1))
snap = log.snapshots[idx]

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Previous", disabled=idx <= 0):
        st.session_state.mpc_step_idx = idx - 1
        st.rerun()
with c2:
    st.write(f"Step **{idx + 1}** / {len(log.snapshots)} · t = **{snap.time_s:.0f} s**")
with c3:
    if st.button("Next", disabled=idx >= len(log.snapshots) - 1):
        st.session_state.mpc_step_idx = idx + 1
        st.rerun()

st.plotly_chart(mpc_horizon_figure(snap), use_container_width=True)
st.caption(snap.caption)
st.write(
    f"Applied power: **{snap.u_applied:.2f} kW** · "
    f"Disturbance estimate d̂ = **{snap.d_hat:.3f}** · "
    f"Solve time: **{snap.solve_ms:.2f} ms**"
)
