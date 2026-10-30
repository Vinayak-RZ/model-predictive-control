import { COLORS } from "./theme.js";

const layoutBase = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: COLORS.surface,
  font: { family: "Inter, system-ui, sans-serif", size: 13, color: COLORS.text },
  margin: { l: 48, r: 24, t: 40, b: 48 },
  legend: { orientation: "h", y: 1.12, x: 0 },
  hovermode: "x unified",
};

export function tripleControlFigure(triple, tempEl, powerEl) {
  const t = triple.mpc.time_s;
  const uMin = triple.params?.u_min ?? 0;
  const uMax = triple.params?.u_max ?? 250;
  const stepAt = triple.params?.ref_step_at_s;
  const distAt = triple.params?.disturbance_at_s;

  const vline = (x, color = COLORS.muted) =>
    x != null && x > 0
      ? [
          {
            type: "line",
            xref: "x",
            yref: "paper",
            x0: x,
            x1: x,
            y0: 0,
            y1: 1,
            line: { dash: "dot", color, width: 1 },
          },
        ]
      : [];

  Plotly.newPlot(
    tempEl,
    [
      { x: t, y: triple.mpc.y_ref, name: "Setpoint", line: { dash: "dash", color: COLORS.text, width: 1.5 } },
      { x: t, y: triple.pid.y_c, name: "PID", line: { color: COLORS.pid, width: 1.7 } },
      { x: t, y: triple.optimized_pid.y_c, name: "Optimized PID", line: { color: COLORS.opt, width: 1.7 } },
      { x: t, y: triple.mpc.y_c, name: "MPC", line: { color: COLORS.mpc, width: 3 } },
    ],
    {
      ...layoutBase,
      height: 300,
      title: { text: "Temperature", font: { size: 14 } },
      xaxis: { title: "Time [s]", gridcolor: COLORS.border },
      yaxis: { title: "°C", gridcolor: COLORS.border },
      shapes: [...vline(stepAt), ...vline(distAt, "#E07A3F")],
    },
    { responsive: true, displayModeBar: false }
  );

  Plotly.newPlot(
    powerEl,
    [
      { x: t, y: triple.pid.u_kw, name: "PID", line: { color: COLORS.pid, width: 1.7 }, showlegend: false },
      { x: t, y: triple.optimized_pid.u_kw, name: "Opt. PID", line: { color: COLORS.opt, width: 1.7 }, showlegend: false },
      { x: t, y: triple.mpc.u_kw, name: "MPC", line: { color: COLORS.mpc, width: 3 }, showlegend: false },
    ],
    {
      ...layoutBase,
      height: 260,
      title: { text: "Heater power", font: { size: 14 } },
      xaxis: { title: "Time [s]", gridcolor: COLORS.border },
      yaxis: { title: "kW", gridcolor: COLORS.border },
      shapes: [
        {
          type: "line",
          xref: "x",
          yref: "y",
          x0: t[0],
          x1: t[t.length - 1],
          y0: uMin,
          y1: uMin,
          line: { dash: "dash", color: COLORS.muted, width: 1 },
        },
        {
          type: "line",
          xref: "x",
          yref: "y",
          x0: t[0],
          x1: t[t.length - 1],
          y0: uMax,
          y1: uMax,
          line: { dash: "dash", color: COLORS.muted, width: 1 },
        },
        ...vline(stepAt),
      ],
    },
    { responsive: true, displayModeBar: false }
  );
}

export function groupedMetricsFigure(rows, scenario, el) {
  const subset = rows.filter((r) => r.Scenario === scenario);
  const controllers = subset.map((r) => r.Controller);
  const metrics = {
    "Limit hits": subset.map((r) => r.Violations),
    "Settling [s]": subset.map((r) => r["Settling [s]"] ?? 0),
    "Overshoot %": subset.map((r) => r["Overshoot %"] ?? 0),
  };
  const names = Object.keys(metrics);
  const colorFor = (c) => {
    const k = c.toLowerCase();
    if (k === "mpc") return COLORS.mpc;
    if (k.includes("opt")) return COLORS.opt;
    return COLORS.pid;
  };
  const order = [...controllers.filter((c) => c.toLowerCase() !== "mpc"), ...controllers.filter((c) => c.toLowerCase() === "mpc")];
  const traces = order.map((ctrl) => {
    const idx = controllers.indexOf(ctrl);
    const isMpc = ctrl.toLowerCase() === "mpc";
    return {
      name: ctrl,
      x: names,
      y: names.map((m) => metrics[m][idx]),
      type: "bar",
      marker: {
        color: colorFor(ctrl),
        line: isMpc ? { width: 1.5, color: COLORS.mpc } : { width: 0 },
      },
      opacity: isMpc ? 1 : 0.88,
      text: names.map((m) => {
        const v = metrics[m][idx];
        return Math.abs(v) >= 10 ? v.toFixed(0) : v.toFixed(1);
      }),
      textposition: "outside",
      cliponaxis: false,
    };
  });
  Plotly.newPlot(
    el,
    traces,
    {
      ...layoutBase,
      barmode: "group",
      height: 380,
      yaxis: { gridcolor: COLORS.border },
      xaxis: { gridcolor: COLORS.border },
    },
    { responsive: true, displayModeBar: false }
  );
}

export function horizonFigure(snap, el) {
  const pred = snap.predicted_y || [];
  const t0 = snap.time_s;
  const x = pred.map((_, i) => t0 + i);
  Plotly.newPlot(
    el,
    [
      {
        x,
        y: pred,
        name: "Predicted T",
        line: { color: COLORS.mpc, width: 3 },
      },
      {
        x: [t0, t0 + Math.max(pred.length - 1, 1)],
        y: [snap.y_ref, snap.y_ref],
        name: "Setpoint",
        line: { dash: "dash", color: COLORS.text, width: 1.5 },
      },
    ],
    {
      ...layoutBase,
      height: 420,
      xaxis: { title: "Time [s]", gridcolor: COLORS.border },
      yaxis: { title: "Temperature [°C]", gridcolor: COLORS.border },
      title: { text: snap.caption || `t = ${t0.toFixed(0)} s`, font: { size: 14 } },
    },
    { responsive: true, displayModeBar: false }
  );
}
