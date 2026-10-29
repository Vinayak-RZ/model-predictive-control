"""Playground: three controllers on one chart with presets and disk-first cache."""

from __future__ import annotations

import numpy as np
import streamlit as st

from mpc_core.sim.config import default_demo_config
from mpc_core.sim.copy_text import (
    PLAYGROUND_CAPTION,
    PLAYGROUND_LEDE,
    PLAYGROUND_TITLE,
)
from mpc_core.sim.pid import PIDGains
from mpc_core.sim.playground import (
    PRESETS,
    PlaygroundParams,
    build_playground_scenario,
    limits_from_playground,
    run_options_from_playground,
    run_triple,
)
from mpc_core.sim.plotly_charts import triple_control_figure
from mpc_core.sim.ui import (
    InsightItem,
    controller_legend,
    inject_styles,
    insight_strip,
    page_header,
    violation_tone,
)
from mpc_core.sim.ui_cache import load_playground_triple

inject_styles()

if "playground_params" not in st.session_state:
    st.session_state.playground_params = PlaygroundParams()


def _params_key(p: PlaygroundParams) -> tuple:
    return tuple(sorted(p.__dict__.items()))


@st.cache_data(show_spinner="Running closed-loop simulations…")
def cached_triple(key: tuple, tune_maxiter: int = 28):
    p = PlaygroundParams(**dict(key))
    scenario = build_playground_scenario(p)
    cfg = default_demo_config()
    limits = limits_from_playground(p, cfg)
    opt = run_options_from_playground(p)
    plain = PIDGains(kp=p.pid_kp, ki=p.pid_ki, kd=p.pid_kd)
    return run_triple(
        scenario,
        cfg=cfg,
        limits=limits,
        options=opt,
        horizon_steps=p.mpc_horizon,
        mpc_tracking_weight=p.mpc_tracking_weight,
        plain_pid_gains=plain,
        tune_maxiter=tune_maxiter,
    )


def resolve_triple(p: PlaygroundParams):
    disk = load_playground_triple(p)
    if disk is not None:
        return disk
    return cached_triple(_params_key(p))


page_header(title=PLAYGROUND_TITLE, look_for=PLAYGROUND_LEDE)
controller_legend()

st.markdown("##### Presets")
pcols = st.columns(5)
preset_actions = [
    ("Setpoint jump", "setpoint_jump"),
    ("Cold-door disturbance", "cold_door"),
    ("Tight power limit", "tight_power"),
    ("Model mismatch", "model_mismatch"),
]
for col, (label, key) in zip(pcols, preset_actions):
    if col.button(label, use_container_width=True):
        st.session_state.playground_params = PRESETS[key](st.session_state.playground_params)
        st.rerun()
if pcols[4].button("Reset defaults", type="secondary", use_container_width=True):
    st.session_state.playground_params = PlaygroundParams()
    st.rerun()

params: PlaygroundParams = st.session_state.playground_params
triple = resolve_triple(params)

chart_col, ctrl_col = st.columns([2.2, 1], gap="large")

with chart_col:
    fig = triple_control_figure(
        mpc=triple.mpc,
        pid=triple.pid,
        opt_pid=triple.optimized_pid,
        u_min=params.u_min,
        u_max=params.u_max,
        step_at_s=params.ref_step_at_s,
        disturbance_at_s=params.disturbance_at_s,
    )
    st.plotly_chart(fig, use_container_width=True)

    insight_items: list[InsightItem] = []
    for name, run in (
        ("MPC", triple.mpc),
        ("PID", triple.pid),
        ("Opt. PID", triple.optimized_pid),
    ):
        m = run.metrics
        word, tone = violation_tone(m.constraint_violation_steps)
        settle = "—" if m.settling_time_s is None else f"{m.settling_time_s:.0f} s"
        insight_items.append(
            InsightItem(
                label=name,
                value=f"IAE {m.iae:.0f} · settle {settle}",
                hint=f"{m.constraint_violation_steps} limit hits · {word}",
                tone=tone,
            )
        )
    insight_strip(insight_items)

    if triple.mpc.mpc_solve_ms is not None:
        avg_ms = float(triple.mpc.mpc_solve_ms.mean())
        p95 = float(np.percentile(triple.mpc.mpc_solve_ms, 95))
        st.caption(f"MPC solve time — mean {avg_ms:.2f} ms / p95 {p95:.2f} ms per step.")

    st.caption(PLAYGROUND_CAPTION)

with ctrl_col:
    with st.form("sliders", border=False):
        p: PlaygroundParams = st.session_state.playground_params

        with st.expander("Scenario", expanded=True):
            ref_high = st.slider("Setpoint high [°C]", 70.0, 180.0, float(p.ref_high_c))
            ref_low = st.slider("Setpoint low [°C]", 60.0, 160.0, float(p.ref_low_c))
            step_at = st.slider("Setpoint step at [s]", 5.0, 120.0, float(p.ref_step_at_s))
            dist_at = st.slider(
                "Disturbance time [s] (0 = none)",
                0.0,
                float(p.duration_s),
                float(p.disturbance_at_s or 0.0),
            )
            dist_kind = st.selectbox(
                "Disturbance",
                ["none", "ambient_step", "heat_loss_bump"],
                index=0
                if not p.disturbance_event
                else (1 if p.disturbance_event == "ambient_step" else 2),
            )
            noise = st.slider("Sensor noise σ [°C]", 0.0, 2.0, float(p.noise_std_c), 0.05)
            mismatch = st.checkbox("Plant/model mismatch", value=p.model_mismatch)

        with st.expander("Limits", expanded=False):
            u_max = st.slider("Power max [kW]", 50.0, 280.0, float(p.u_max))
            du_max = st.slider("Max power step [kW/s]", 2.0, 40.0, float(p.du_max))

        with st.expander("Controllers", expanded=False):
            kp = st.slider("PID Kp", 0.1, 10.0, float(p.pid_kp), 0.1)
            ki = st.slider("PID Ki", 0.0, 0.3, float(p.pid_ki), 0.005)
            kd = st.slider("PID Kd", 0.0, 5.0, float(p.pid_kd), 0.1)
            horizon = st.slider("MPC horizon [steps]", 5, 40, int(p.mpc_horizon))
            q_weight = st.slider(
                "MPC tracking weight", 0.2, 5.0, float(p.mpc_tracking_weight), 0.1
            )

        submitted = st.form_submit_button(
            "Update simulation", type="primary", use_container_width=True
        )

    if submitted:
        ev = None if dist_kind == "none" or dist_at <= 0 else dist_kind
        st.session_state.playground_params = PlaygroundParams(
            duration_s=p.duration_s,
            t_initial_c=p.t_initial_c,
            u_initial_kw=p.u_initial_kw,
            ref_low_c=ref_low,
            ref_high_c=ref_high,
            ref_step_at_s=step_at,
            disturbance_at_s=None if ev is None else dist_at,
            disturbance_event=ev,
            u_min=p.u_min,
            u_max=u_max,
            du_max=du_max,
            noise_std_c=noise,
            noise_seed=p.noise_seed,
            model_mismatch=mismatch,
            mpc_horizon=horizon,
            mpc_tracking_weight=q_weight,
            pid_kp=kp,
            pid_ki=ki,
            pid_kd=kd,
            enforce_pid_rate=p.enforce_pid_rate,
        )
        st.rerun()

    tg = triple.tune.gains
    st.markdown("##### Optimised PID gains")
    st.caption(
        f"Kp = **{tg.kp:.3g}**, Ki = **{tg.ki:.3g}**, Kd = **{tg.kd:.3g}** "
        "(minimise IAE + violation penalty on this scenario)."
    )
