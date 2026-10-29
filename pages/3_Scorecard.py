"""Scorecard across named scenarios for MPC, PID, and optimized PID."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from mpc_core.sim.config import default_demo_config
from mpc_core.sim.metrics import SimulationMetrics
from mpc_core.sim.playground import run_triple
from mpc_core.sim.plotly_charts import metrics_bar_chart
from mpc_core.sim.scenarios import SCENARIOS, ScenarioConfig
from mpc_core.sim.simulate import RunOptions

st.set_page_config(page_title="Scorecard", layout="wide")

st.markdown(
    "**This screen** runs the same scenarios for MPC, hand-tuned PID, and optimized PID, "
    "then tabulates IAE, overshoot, settling time, energy, and constraint violations."
)


def _scenario_list() -> list[tuple[str, ScenarioConfig, RunOptions | None]]:
    items: list[tuple[str, ScenarioConfig, RunOptions | None]] = [
        (k, SCENARIOS[k], None) for k in SCENARIOS
    ]
    mismatch = SCENARIOS["setpoint_tracking"]
    items.append(
        (
            "model_mismatch",
            mismatch,
            RunOptions(model_mismatch=True, noise_seed=42),
        )
    )
    return items


@st.cache_data(show_spinner="Running scorecard simulations (includes PID tuning)…")
def scorecard_rows():
    cfg = default_demo_config()
    rows = []
    for key, scenario, opt in _scenario_list():
        triple = run_triple(scenario, cfg=cfg, options=opt, tune_maxiter=30)
        for label, run in (
            ("MPC", triple.mpc),
            ("PID", triple.pid),
            ("Optimized PID", triple.optimized_pid),
        ):
            m: SimulationMetrics = run.metrics
            rows.append(
                {
                    "Scenario": key.replace("_", " ").title(),
                    "Controller": label,
                    "IAE": m.iae,
                    "Overshoot %": m.overshoot_pct,
                    "Settling [s]": m.settling_time_s,
                    "Energy [kWh]": m.energy_kwh,
                    "Violations": m.constraint_violation_steps,
                }
            )
    return pd.DataFrame(rows)


df = scorecard_rows()
st.dataframe(
    df.style.format(
        {
            "IAE": "{:.0f}",
            "Overshoot %": "{:.1f}",
            "Settling [s]": "{:.0f}",
            "Energy [kWh]": "{:.2f}",
            "Violations": "{:.0f}",
        },
        na_rep="—",
    ),
    use_container_width=True,
    hide_index=True,
)

scenario_pick = st.selectbox("Bar charts for scenario", df["Scenario"].unique())
subset = df[df["Scenario"] == scenario_pick]
for metric in ("IAE", "Settling [s]", "Violations"):
    fig = metrics_bar_chart(
        subset["Controller"].tolist(),
        subset[metric].fillna(0).tolist(),
        title=f"{metric} — {scenario_pick}",
    )
    st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Lower IAE and violations are better; settling time only applies once the band is reached. "
    "Model mismatch shrinks MPC's margin — compare that row honestly."
)
