"""Plotly figures for the Streamlit teaching UI."""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from mpc_core.sim.simulate import SimulationResult

ACCENT = "#2563eb"
MPC_COLOR = ACCENT
PID_COLOR = "#71717a"
OPT_PID_COLOR = "#0d9488"


def triple_control_figure(
    *,
    mpc: SimulationResult,
    pid: SimulationResult,
    opt_pid: SimulationResult,
    u_min: float,
    u_max: float,
) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("Temperature", "Heater power"),
    )
    t = mpc.time_s
    fig.add_trace(
        go.Scatter(x=t, y=mpc.y_ref, name="Setpoint", line=dict(dash="dash", color="#18181b")),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=t, y=mpc.y_c, name="MPC", line=dict(color=MPC_COLOR, width=2.5)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=t, y=pid.y_c, name="PID", line=dict(color=PID_COLOR, width=2)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=t,
            y=opt_pid.y_c,
            name="Optimized PID",
            line=dict(color=OPT_PID_COLOR, width=2),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=t, y=mpc.u_kw, name="MPC power", line=dict(color=MPC_COLOR), showlegend=False),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=t, y=pid.u_kw, name="PID power", line=dict(color=PID_COLOR), showlegend=False),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=t,
            y=opt_pid.u_kw,
            name="Opt. PID power",
            line=dict(color=OPT_PID_COLOR),
            showlegend=False,
        ),
        row=2,
        col=1,
    )
    for yv in (u_min, u_max):
        fig.add_hline(
            y=yv,
            line_dash="dash",
            line_color="#a1a1aa",
            row=2,
            col=1,
        )
    fig.update_yaxes(title_text="°C", row=1, col=1)
    fig.update_yaxes(title_text="kW", row=2, col=1)
    fig.update_xaxes(title_text="Time [s]", row=2, col=1)
    fig.update_layout(
        height=620,
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        template="plotly_white",
    )
    return fig


def mpc_horizon_figure(snapshot) -> go.Figure:
    """Fan of predicted temperature from one MPC step."""
    h = len(snapshot.predicted_y)
    future_t = [snapshot.time_s + i for i in range(1, h + 1)]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[snapshot.time_s],
            y=[snapshot.y_meas],
            mode="markers",
            name="Measured now",
            marker=dict(size=10, color=ACCENT),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=future_t,
            y=snapshot.predicted_y,
            mode="lines+markers",
            name="Predicted temperature",
            line=dict(color=ACCENT, width=2.5),
        )
    )
    fig.add_hline(
        y=snapshot.y_ref,
        line_dash="dash",
        line_color="#18181b",
        annotation_text="Setpoint",
    )
    fig.update_layout(
        height=420,
        xaxis_title="Time [s]",
        yaxis_title="Temperature [°C]",
        template="plotly_white",
        margin=dict(l=40, r=20, t=30, b=40),
    )
    return fig


def metrics_bar_chart(labels: list[str], values: list[float], title: str) -> go.Figure:
    fig = go.Figure(go.Bar(x=labels, y=values, marker_color=ACCENT))
    fig.update_layout(title=title, template="plotly_white", height=320, margin=dict(t=50))
    return fig
