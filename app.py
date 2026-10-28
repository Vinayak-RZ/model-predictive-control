"""Interactive MPC vs PID comparison for the heater coursework demo."""

from __future__ import annotations

import streamlit as st

from mpc_core.sim.config import default_demo_config
from mpc_core.sim.plotting import format_metrics_table, save_comparison_figure
from mpc_core.sim.scenarios import SCENARIOS, ScenarioConfig
from mpc_core.sim.simulate import run_closed_loop
from mpc_core.thresholds import SetpointLimits

st.set_page_config(
    page_title="Heater MPC vs PID",
    page_icon="🔥",
    layout="wide",
)

cfg = default_demo_config()

st.title("Heater control: MPC vs PID")
st.markdown(
    """
This demo runs **offset-free model predictive control** (SciPy L-BFGS-B on an
identified linear model) against a **tuned PID** baseline on a **CasADi
heat-balance heater model**. Numbers are illustrative coursework values, not
plant data.
"""
)

with st.expander("What is MPC doing here?", expanded=False):
    st.markdown(
        """
- **Prediction horizon:** the controller rolls the linear model forward
  `N` steps and sums squared temperature errors to a setpoint.
- **Optimisation each step:** SciPy finds the best *constant* coil power over
  the horizon subject to power bounds and a max move per step.
- **Receding horizon:** only the first power move is applied; at the next sample
  the whole optimisation is repeated with a new measurement.
- **Constraints:** box limits on power and rate limits are enforced inside the
  optimiser; active limits are reported after each solve.
- **Offset-free:** an integrating disturbance state `d_hat` is updated from the
  one-step innovation so model mismatch and load changes are rejected faster.
        """
    )

col_left, col_right = st.columns([1, 2])

with col_left:
    scenario_key = st.selectbox(
        "Scenario",
        options=list(SCENARIOS.keys()),
        format_func=lambda k: SCENARIOS[k].title,
    )
    scenario: ScenarioConfig = SCENARIOS[scenario_key]
    st.caption(scenario.description)

    horizon = st.slider(
        "MPC horizon (steps)",
        min_value=5,
        max_value=40,
        value=scenario.mpc_horizon or cfg.horizon_steps,
    )
    u_low = st.number_input("Power min [kW]", value=float(cfg.limits.low))
    u_high = st.number_input("Power max [kW]", value=float(cfg.limits.high))
    du_max = st.number_input("Max power step [kW]", value=float(cfg.limits.max_step))
    run_btn = st.button("Run simulation", type="primary")

with col_right:
    if run_btn:
        limits = SetpointLimits(
            cfg.setpoint_id,
            cfg.limits.unit,
            float(u_low),
            float(u_high),
            float(du_max),
        )
        with st.spinner("Simulating heater plant…"):
            mpc = run_closed_loop(
                scenario,
                "mpc",
                horizon_steps=horizon,
                limits=limits,
            )
            pid = run_closed_loop(
                scenario,
                "pid",
                limits=limits,
            )
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / "compare.png"
            save_comparison_figure(
                title=scenario.title,
                mpc=mpc,
                pid=pid,
                path=png,
            )
            st.image(str(png), use_container_width=True)

        st.subheader("Metrics")
        st.markdown(format_metrics_table(mpc.metrics, pid.metrics))
        if mpc.active_constraints_last:
            st.info(f"MPC active constraints (last step): {', '.join(mpc.active_constraints_last)}")
    else:
        st.info("Choose a scenario and click **Run simulation** to compare controllers.")

st.divider()
st.caption(
    "Run locally: `pip install -r requirements.txt && streamlit run app.py` · "
    "Batch plots: `python examples/run_simulations.py`"
)
