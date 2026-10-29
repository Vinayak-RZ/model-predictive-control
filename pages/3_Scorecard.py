"""Scorecard across named scenarios for MPC, PID, and optimized PID."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from mpc_core.sim.config import default_demo_config
from mpc_core.sim.metrics import SimulationMetrics
from mpc_core.sim.playground import run_triple
from mpc_core.sim.plotly_charts import grouped_metrics_figure, metrics_bar_chart
from mpc_core.sim.scenarios import SCENARIOS, ScenarioConfig
from mpc_core.sim.simulate import RunOptions
from mpc_core.sim.ui import inject_styles, page_header, sidebar_brand, takeaway

st.set_page_config(page_title="Scorecard · MPC Heater Lab", layout="wide")
inject_styles()
sidebar_brand()

page_header(
    eyebrow="Proof",
    title="Scorecard",
    look_for=(
        "Same plant, noise, and limits for MPC, hand-tuned PID, and optimized PID. "
        "Lower IAE and violations are better; settling only counts once the band is reached."
    ),
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

# Lead with power-limits story from existing data
power_label = "Power Constraints"
if power_label not in df["Scenario"].unique():
    # Fallback: match by substring
    power_rows = df[df["Scenario"].str.contains("Power", case=False)]
else:
    power_rows = df[df["Scenario"] == power_label]

if not power_rows.empty:
    viol = {
        row["Controller"]: int(row["Violations"])
        for _, row in power_rows.iterrows()
    }
    mpc_v = viol.get("MPC", 0)
    pid_v = viol.get("PID", 0)
    opt_v = viol.get("Optimized PID", 0)
    takeaway(
        label="Demo takeaway · power limits",
        body=(
            f"On the power-limits scenario, plain PID records **{pid_v}** constraint "
            f"violation steps while MPC stays at **{mpc_v}** and optimized PID at **{opt_v}**. "
            "MPC plans ahead within slew and power bounds; the hand-tuned PID hits the rate limit."
        ),
    )

scenario_pick = st.selectbox("Scenario", df["Scenario"].unique())
subset = df[df["Scenario"] == scenario_pick].copy()
controllers = subset["Controller"].tolist()

fig = grouped_metrics_figure(
    controllers,
    {
        "IAE": subset["IAE"].fillna(0).tolist(),
        "Settling [s]": subset["Settling [s]"].fillna(0).tolist(),
        "Violations": subset["Violations"].fillna(0).tolist(),
    },
    title=f"Controller comparison — {scenario_pick}",
)
st.plotly_chart(fig, use_container_width=True)

detail_cols = st.columns(3)
for col, metric in zip(detail_cols, ("IAE", "Settling [s]", "Violations")):
    with col:
        fig_m = metrics_bar_chart(
            subset["Controller"].tolist(),
            subset[metric].fillna(0).tolist(),
            title=metric,
            y_title=metric,
        )
        st.plotly_chart(fig_m, use_container_width=True)

st.markdown("##### Full metrics table")
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

st.caption(
    "Model mismatch shrinks MPC's margin; compare that row honestly. "
    "Optimized PID gains are retuned per scenario on the same plant and noise seed."
)
