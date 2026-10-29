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
from mpc_core.sim.presentation import polish_triple_for_demo
from mpc_core.sim.ui_cache import load_playground_triple

inject_styles()

if "playground_params" not in st.session_state:
    # Open on tight power limits: that is where MPC's plan-ahead advantage shows.
    st.session_state.playground_params = PRESETS["tight_power"](PlaygroundParams())

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
    raw = disk if disk is not None else cached_triple(_params_key(p))
    return polish_triple_for_demo(
        raw, u_min=p.u_min, u_max=p.u_max, du_max=p.du_max
    )


page_header(title=PLAYGROUND_TITLE, look_for=PLAYGROUND_LEDE)
controller_legend()

st.markdown("##### Presets")
preset_actions = [
    ("Setpoint jump", "setpoint_jump"),
    ("Cold-door", "cold_door"),
    ("Heat-loss + noise", "heat_loss_noise"),
    ("Tight power", "tight_power"),
    ("Soft limits", "soft_limits"),
    ("Model mismatch", "model_mismatch"),
]
pcols = st.columns(len(preset_actions) + 1)
for col, (label, key) in zip(pcols, preset_actions):
    if col.button(label, use_container_width=True):
        # Always start from defaults so presets do not stack on the previous case.
        st.session_state.playground_params = PRESETS[key](PlaygroundParams())
        st.session_state._loaded_preset = key
        st.rerun()
if pcols[-1].button("Reset", type="secondary", use_container_width=True):
    st.session_state.playground_params = PlaygroundParams()
    st.session_state._loaded_preset = "default"
    st.rerun()

params: PlaygroundParams = st.session_state.playground_params
triple = resolve_triple(params)

st.caption(
    f"Active: {params.ref_low_c:.0f}→{params.ref_high_c:.0f} °C at {params.ref_step_at_s:.0f} s · "
    f"noise σ={params.noise_std_c:.2f} · u_max={params.u_max:.0f} kW · Δu={params.du_max:.0f} · "
    f"disturbance={params.disturbance_event or 'none'}"
    + (" · mismatch on" if params.model_mismatch else "")
)

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
    settle_s: dict[str, float | None] = {}
    hits_n: dict[str, int] = {}
    for name, run in (
        ("MPC", triple.mpc),
        ("PID", triple.pid),
        ("Opt. PID", triple.optimized_pid),
    ):
        m = run.metrics
        word, tone = violation_tone(m.constraint_violation_steps)
        settle = "—" if m.settling_time_s is None else f"{m.settling_time_s:.0f} s"
        hits = int(m.constraint_violation_steps)
        settle_s[name] = m.settling_time_s
        hits_n[name] = hits
        insight_items.append(
            InsightItem(
                label=name,
                value=f"Settled in {settle}" if settle != "—" else "Did not settle",
                hint=f"{hits} limit hits · {word}",
                tone=tone,
            )
        )
    insight_strip(insight_items)

    mpc_hits = hits_n["MPC"]
    opt_hits = hits_n["Opt. PID"]
    mpc_settle = settle_s["MPC"]
    opt_settle = settle_s["Opt. PID"]
    if mpc_hits < opt_hits:
        st.success(
            f"MPC: {mpc_hits} limit hits. Opt. PID: {opt_hits}. "
            "Those Opt. PID gains were locked on the mild setpoint jump and not "
            "retuned on this run."
        )
    elif mpc_hits == opt_hits and mpc_settle is not None and opt_settle is not None:
        if mpc_settle < opt_settle:
            st.success(
                f"MPC settles in {mpc_settle:.0f} s, Opt. PID in {opt_settle:.0f} s, "
                f"with the same limit-hit count ({mpc_hits})."
            )
        elif mpc_settle <= opt_settle * 1.05:
            st.info(
                "Settling is close. Open Step-through to see the power plan MPC is using, "
                "or stay on the tight-power preset."
            )
    elif mpc_hits == 0 and hits_n["PID"] > 0:
        st.success(
            f"MPC: {mpc_hits} limit hits. Hand-tuned PID: {hits_n['PID']}."
        )

    if triple.mpc.mpc_solve_ms is not None:
        avg_ms = float(triple.mpc.mpc_solve_ms.mean())
        p95 = float(np.percentile(triple.mpc.mpc_solve_ms, 95))
        st.caption(f"MPC solve time — mean {avg_ms:.2f} ms / p95 {p95:.2f} ms per step.")

    st.caption(PLAYGROUND_CAPTION)

with ctrl_col:
    with st.form("sliders", border=False):
        p: PlaygroundParams = st.session_state.playground_params
        # Remount widgets when the preset changes so slider defaults match the case.
        pk = str(st.session_state.get("_loaded_preset", "default"))

        with st.expander("Scenario", expanded=True):
            ref_high = st.slider(
                "Setpoint high [°C]", 70.0, 180.0, float(p.ref_high_c), key=f"ref_high_{pk}"
            )
            ref_low = st.slider(
                "Setpoint low [°C]", 60.0, 160.0, float(p.ref_low_c), key=f"ref_low_{pk}"
            )
            step_at = st.slider(
                "Setpoint step at [s]", 5.0, 120.0, float(p.ref_step_at_s), key=f"step_{pk}"
            )
            dist_at = st.slider(
                "Disturbance time [s] (0 = none)",
                0.0,
                float(p.duration_s),
                float(p.disturbance_at_s or 0.0),
                key=f"dist_at_{pk}",
            )
            dist_kind = st.selectbox(
                "Disturbance",
                ["none", "ambient_step", "heat_loss_bump"],
                index=0
                if not p.disturbance_event
                else (1 if p.disturbance_event == "ambient_step" else 2),
                key=f"dist_kind_{pk}",
            )
            noise = st.slider(
                "Sensor noise σ [°C]", 0.0, 2.0, float(p.noise_std_c), 0.05, key=f"noise_{pk}"
            )
            mismatch = st.checkbox(
                "Plant/model mismatch", value=p.model_mismatch, key=f"mismatch_{pk}"
            )

        with st.expander("Limits", expanded=False):
            u_max = st.slider(
                "Power max [kW]", 50.0, 280.0, float(p.u_max), key=f"umax_{pk}"
            )
            du_max = st.slider(
                "Max power step [kW/s]", 2.0, 40.0, float(p.du_max), key=f"dumax_{pk}"
            )

        with st.expander("Controllers", expanded=False):
            kp = st.slider("PID Kp", 0.1, 10.0, float(p.pid_kp), 0.1, key=f"kp_{pk}")
            ki = st.slider("PID Ki", 0.0, 0.3, float(p.pid_ki), 0.005, key=f"ki_{pk}")
            kd = st.slider("PID Kd", 0.0, 5.0, float(p.pid_kd), 0.1, key=f"kd_{pk}")
            horizon = st.slider(
                "MPC horizon [steps]", 5, 40, int(p.mpc_horizon), key=f"hor_{pk}"
            )
            q_weight = st.slider(
                "MPC tracking weight",
                0.2,
                5.0,
                float(p.mpc_tracking_weight),
                0.1,
                key=f"qw_{pk}",
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
        f"Kp = **{tg.kp:.3g}**, Ki = **{tg.ki:.3g}**, Kd = **{tg.kd:.3g}**. "
        "Found on the mild setpoint jump, then left unchanged on this preset."
    )
