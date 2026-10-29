"""Plotly figures for the Streamlit teaching UI (DESIGN.md chart tokens)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from mpc_core.sim.theme import (
    ACCENT,
    BORDER,
    COBALT,
    COPPER,
    MPC_COLOR,
    OPT_PID_COLOR,
    PID_COLOR,
    SURFACE_SUBTLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

if TYPE_CHECKING:
    from mpc_core.sim.simulate import SimulationResult


def _base_layout(**kwargs) -> dict:
    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=SURFACE_SUBTLE,
        font=dict(family="Inter, system-ui, sans-serif", size=14, color=TEXT_PRIMARY),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.12,
            x=0,
            font=dict(size=13),
        ),
        margin=dict(l=48, r=24, t=72, b=48),
        hovermode="x unified",
    )
    layout.update(kwargs)
    return layout


def _style_axes(fig: go.Figure) -> None:
    fig.update_xaxes(
        showgrid=True,
        gridcolor=BORDER,
        zeroline=False,
        title_font=dict(size=13, color=TEXT_SECONDARY),
        tickfont=dict(size=12, color=TEXT_MUTED),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=BORDER,
        zeroline=False,
        title_font=dict(size=13, color=TEXT_SECONDARY),
        tickfont=dict(size=12, color=TEXT_MUTED),
    )


def triple_control_figure(
    *,
    mpc: SimulationResult,
    pid: SimulationResult,
    opt_pid: SimulationResult,
    u_min: float,
    u_max: float,
    step_at_s: float | None = None,
    disturbance_at_s: float | None = None,
) -> go.Figure:
    from mpc_core.sim.presentation import PRESENTATION_DEMO

    # In the presentation deck, draw MPC on top and a touch heavier so it reads first.
    mpc_w = 3.0 if PRESENTATION_DEMO else 2.5
    other_w = 1.7 if PRESENTATION_DEMO else 2.0
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=("Temperature", "Heater power"),
    )
    t = mpc.time_s
    fig.add_trace(
        go.Scatter(
            x=t,
            y=mpc.y_ref,
            name="Setpoint",
            line=dict(dash="dash", color=TEXT_PRIMARY, width=1.5),
        ),
        row=1,
        col=1,
    )
    # PID / Opt first, MPC last so the winner sits on top of the stack.
    fig.add_trace(
        go.Scatter(x=t, y=pid.y_c, name="PID", line=dict(color=PID_COLOR, width=other_w)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=t,
            y=opt_pid.y_c,
            name="Optimized PID",
            line=dict(color=OPT_PID_COLOR, width=other_w),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=t, y=mpc.y_c, name="MPC", line=dict(color=MPC_COLOR, width=mpc_w)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=t,
            y=pid.u_kw,
            name="PID power",
            line=dict(color=PID_COLOR, width=other_w),
            showlegend=False,
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=t,
            y=opt_pid.u_kw,
            name="Opt. PID power",
            line=dict(color=OPT_PID_COLOR, width=other_w),
            showlegend=False,
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=t,
            y=mpc.u_kw,
            name="MPC power",
            line=dict(color=MPC_COLOR, width=mpc_w),
            showlegend=False,
        ),
        row=2,
        col=1,
    )
    for yv in (u_min, u_max):
        fig.add_hline(
            y=yv,
            line_dash="dash",
            line_color=TEXT_MUTED,
            line_width=1,
            row=2,
            col=1,
        )

    if step_at_s is not None and step_at_s > 0:
        for row in (1, 2):
            fig.add_vline(
                x=step_at_s,
                line_dash="dot",
                line_color=TEXT_MUTED,
                line_width=1,
                row=row,
                col=1,
            )
        fig.add_annotation(
            x=step_at_s,
            y=1.02,
            yref="paper",
            text="Setpoint step",
            showarrow=False,
            font=dict(size=11, color=TEXT_MUTED),
            xanchor="left",
        )

    if disturbance_at_s is not None and disturbance_at_s > 0:
        for row in (1, 2):
            fig.add_vline(
                x=disturbance_at_s,
                line_dash="dot",
                line_color=COPPER,
                line_width=1.5,
                row=row,
                col=1,
            )
        fig.add_annotation(
            x=disturbance_at_s,
            y=0.98,
            yref="paper",
            text="Disturbance",
            showarrow=False,
            font=dict(size=11, color=COPPER),
            xanchor="left",
        )

    fig.update_yaxes(title_text="°C", row=1, col=1)
    fig.update_yaxes(title_text="kW", row=2, col=1)
    fig.update_xaxes(title_text="Time [s]", row=2, col=1)
    fig.update_layout(**_base_layout(height=640))
    fig.update_annotations(font=dict(size=14, color=TEXT_SECONDARY))
    _style_axes(fig)
    return fig


def mpc_horizon_figure(snapshot) -> go.Figure:
    """Fan of predicted temperature from one MPC step."""
    h = len(snapshot.predicted_y)
    future_t = [snapshot.time_s + i for i in range(1, h + 1)]
    fig = go.Figure()

    # Soft past / future bands only (no overlapping annotation text).
    fig.add_vrect(
        x0=snapshot.time_s - 8,
        x1=snapshot.time_s,
        fillcolor=BORDER,
        opacity=0.35,
        layer="below",
        line_width=0,
    )
    fig.add_vrect(
        x0=snapshot.time_s,
        x1=future_t[-1] if future_t else snapshot.time_s + 1,
        fillcolor=COBALT,
        opacity=0.04,
        layer="below",
        line_width=0,
    )

    fig.add_trace(
        go.Scatter(
            x=[snapshot.time_s],
            y=[snapshot.y_meas],
            mode="markers",
            name="Measured now",
            marker=dict(size=14, color=ACCENT, line=dict(width=2, color=TEXT_PRIMARY)),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=future_t,
            y=snapshot.predicted_y,
            mode="lines+markers",
            name="Predicted temperature",
            line=dict(color=ACCENT, width=2.5),
            marker=dict(size=6, color=ACCENT),
        )
    )
    if future_t:
        fig.add_trace(
            go.Scatter(
                x=[future_t[0]],
                y=[snapshot.predicted_y[0]],
                mode="markers",
                name="After first move",
                marker=dict(size=12, symbol="diamond", color=ACCENT),
                showlegend=True,
            )
        )
    fig.add_hline(
        y=snapshot.y_ref,
        line_dash="dash",
        line_color=TEXT_PRIMARY,
        line_width=1.5,
        annotation_text="Setpoint",
        annotation_position="top right",
        annotation_font=dict(size=12, color=TEXT_PRIMARY),
    )
    fig.update_layout(
        **_base_layout(
            height=460,
            xaxis_title="Time [s]",
            yaxis_title="Temperature [°C]",
            margin=dict(l=48, r=24, t=56, b=48),
        )
    )
    _style_axes(fig)
    return fig


def metrics_bar_chart(
    labels: list[str],
    values: list[float],
    title: str,
    *,
    y_title: str | None = None,
) -> go.Figure:
    colors = [controller_color(label) for label in labels]
    text = [f"{v:.0f}" if abs(v) >= 10 else f"{v:.1f}" for v in values]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=colors,
            text=text,
            textposition="outside",
            cliponaxis=False,
        )
    )
    fig.update_layout(
        **_base_layout(
            title=dict(text=title, font=dict(size=16, color=TEXT_PRIMARY)),
            height=340,
            margin=dict(l=40, r=20, t=60, b=40),
            showlegend=False,
            yaxis_title=y_title,
        )
    )
    _style_axes(fig)
    return fig


def controller_color(label: str) -> str:
    key = label.strip().lower()
    if key == "mpc":
        return MPC_COLOR
    if key in ("optimized pid", "opt. pid", "opt pid"):
        return OPT_PID_COLOR
    return PID_COLOR


def grouped_metrics_figure(
    controllers: list[str],
    metrics: dict[str, list[float]],
    *,
    title: str,
) -> go.Figure:
    """Side-by-side controller bars for several metrics on one figure."""
    from mpc_core.sim.presentation import PRESENTATION_DEMO

    fig = go.Figure()
    metric_names = list(metrics.keys())
    draw_order = list(controllers)
    if PRESENTATION_DEMO and any(c.strip().lower() == "mpc" for c in controllers):
        draw_order = [c for c in controllers if c.strip().lower() != "mpc"] + [
            c for c in controllers if c.strip().lower() == "mpc"
        ]
    for ctrl in draw_order:
        idx = controllers.index(ctrl)
        ys = [metrics[m][idx] for m in metric_names]
        is_mpc = ctrl.strip().lower() == "mpc"
        fig.add_trace(
            go.Bar(
                name=ctrl,
                x=metric_names,
                y=ys,
                marker_color=controller_color(ctrl),
                marker_line=dict(
                    width=1.5 if (PRESENTATION_DEMO and is_mpc) else 0,
                    color=MPC_COLOR if is_mpc else "rgba(0,0,0,0)",
                ),
                text=[f"{v:.0f}" if abs(v) >= 10 else f"{v:.1f}" for v in ys],
                textposition="outside",
                cliponaxis=False,
                opacity=1.0 if (not PRESENTATION_DEMO or is_mpc) else 0.88,
            )
        )
    layout_kwargs: dict = dict(
        barmode="group",
        height=380,
        margin=dict(l=40, r=20, t=56, b=48),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, xanchor="left"),
    )
    if title:
        layout_kwargs["title"] = dict(
            text=title, font=dict(size=16, color=TEXT_PRIMARY), y=0.98
        )
        layout_kwargs["margin"] = dict(l=40, r=20, t=72, b=48)
        layout_kwargs["legend"] = dict(
            orientation="h", yanchor="top", y=-0.2, x=0, xanchor="left"
        )
        layout_kwargs["margin"] = dict(l=40, r=20, t=56, b=72)
    fig.update_layout(**_base_layout(**layout_kwargs))
    _style_axes(fig)
    return fig
