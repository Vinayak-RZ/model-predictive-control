"""Scorecard across named scenarios."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from mpc_core.sim.copy_text import (
    SCORECARD_LEDE,
    SCORECARD_POWER_TEMPLATE,
    SCORECARD_TITLE,
)
from mpc_core.sim.plotly_charts import grouped_metrics_figure
from mpc_core.sim.ui import inject_styles, page_header
from mpc_core.sim.ui_cache import load_scorecard_rows

inject_styles()

page_header(title=SCORECARD_TITLE, look_for=SCORECARD_LEDE)


rows = load_scorecard_rows()
if rows is None:
    st.error("Missing data/ui/scorecard.json. Run: python scripts/precompute_ui_data.py")
    st.stop()
df = pd.DataFrame(rows)

power_rows = df[df["Scenario"].str.contains("Power", case=False)]
if not power_rows.empty:
    viol = {row["Controller"]: int(row["Violations"]) for _, row in power_rows.iterrows()}
    st.markdown(
        SCORECARD_POWER_TEMPLATE.format(
            pid_n=viol.get("PID", 0),
            mpc_n=viol.get("MPC", 0),
            opt_n=viol.get("Optimized PID", 0),
        )
    )

scenario_pick = st.selectbox("Scenario", df["Scenario"].unique())
subset = df[df["Scenario"] == scenario_pick].copy()
controllers = subset["Controller"].tolist()

st.markdown(f"##### {scenario_pick}")
fig = grouped_metrics_figure(
    controllers,
    {
        "IAE": subset["IAE"].fillna(0).tolist(),
        "Settling [s]": subset["Settling [s]"].fillna(0).tolist(),
        "Violations": subset["Violations"].fillna(0).tolist(),
    },
    title="",
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("##### Metrics table")
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
