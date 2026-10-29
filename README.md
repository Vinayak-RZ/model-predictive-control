<p align="center">
  <img src="assets/mpc-heater-lab-logo.svg" width="168" alt="MPC Heater Lab helper">
</p>

<h1 align="center">
  <img src="assets/mpc-heater-lab-wordmark.svg" width="380" alt="MPC Heater Lab">
</h1>

<p align="center">
  <strong>Offset-free MPC vs hand-tuned PID vs optimized PID on a heat-balance heater model.</strong>
</p>

<p align="center">
  <a href="#quick-start"><b>Quick start</b></a> ·
  <a href="#interactive-app"><b>Interactive app</b></a> ·
  <a href="#showcase-video"><b>Video</b></a> ·
  <a href="HOW-IT-WORKS.md"><b>How it works</b></a> ·
  <a href="report/report.md"><b>Report</b></a>
</p>

Three scripted scenarios, a **multipage Streamlit lab**, batch plots under `results/`, and an **82 s showcase video** (HyperFrames) driven by the same simulation JSON as the app.

> Coursework simulation you can run today — not a field PLC program.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
python3 -m pytest -q
python3 examples/run_simulations.py
streamlit run app.py
```

## Interactive app

**Playground** — compare MPC, PID, and optimized PID on one chart; presets, cached runs, MPC solve time.

<img src="docs/streamlit-playground.png" width="900" alt="Streamlit Playground: temperature and heater power traces for MPC, PID, and optimized PID">

**Step-through** — walk the receding horizon one MPC step at a time.

<img src="docs/streamlit-step-through.png" width="900" alt="Streamlit Step-through: MPC predicted temperature fan over the horizon">

**Scorecard** — same scenarios as batch runs; violations, settling, IAE (including model mismatch).

<img src="docs/streamlit-scorecard.png" width="900" alt="Streamlit Scorecard: metrics table and bar charts">

Theme: `.streamlit/config.toml` (projector-friendly accent `#2563eb`).

## Showcase video

The cut focuses on **power limits and violations**: plain PID breaks slew rules (6 violation steps); MPC stays feasible with zero violations by planning ahead; optimized PID is shown honestly at zero violations after scenario-specific retuning.

<p align="center">
  <a href="https://raw.githubusercontent.com/Vinayak-RZ/model-predictive-control/main/video/out/mpc-vs-pid.mp4">
    <img src="docs/video-poster.png" width="720" alt="Play showcase video (poster)">
  </a>
</p>

<p align="center">
  <video src="https://raw.githubusercontent.com/Vinayak-RZ/model-predictive-control/main/video/out/mpc-vs-pid.mp4" controls width="720" poster="docs/video-poster.png">
    Your browser does not support inline video. <a href="https://raw.githubusercontent.com/Vinayak-RZ/model-predictive-control/main/video/out/mpc-vs-pid.mp4">Download the MP4</a>.
  </video>
</p>

<p align="center">
  <img src="docs/demo-preview.gif" width="720" alt="10 s preview of the power-limit animation">
</p>

**Repo copy:** [`video/out/mpc-vs-pid.mp4`](video/out/mpc-vs-pid.mp4) · **Duration:** 82 s · **Size:** ~1.8 MB · **Source:** [`video/index.html`](video/index.html) + [`video/data/`](video/data/) from `python3 scripts/export_video_data.py`.

## Proof (batch metrics)

From [`results/metrics_summary.json`](results/metrics_summary.json) after `python3 examples/run_simulations.py`:

| Scenario | Metric | MPC | PID | Optimized PID |
| --- | --- | --- | --- | --- |
| Setpoint tracking | IAE | 1824 | 2477 | 1466 |
| Setpoint tracking | Settling [s] | **101** | 179 | 99 |
| Disturbance rejection | IAE | 955 | 1090 | **586** |
| Disturbance rejection | Settling [s] | 62 | 103 | **60** |
| Power limits | Violations | **0** | **6** | **0** |
| Power limits | IAE | 9480 | 9153* | 9033 |
| Model mismatch | IAE | 2009 | 2541 | 1667 |
| Model mismatch | Settling [s] | **111** | 167 | 109 |

\*PID lower IAE only with **slew violations** (rate limit not enforced in that scenario baseline).

Simulation plots:

| Setpoint | Disturbance | Power limits |
| --- | --- | --- |
| ![Setpoint](results/setpoint_tracking.png) | ![Disturbance](results/disturbance_rejection.png) | ![Power](results/power_constraints.png) |

**Fair comparison:** optimized PID gains come from SciPy (`src/mpc_core/sim/pid_tune.py`) minimizing IAE plus a violation penalty on the **same** plant, noise seed, and limits. Heater power is clipped to `[u_min, u_max]` every step.

## How it works

```text
  y_meas ──► offset-free MPC (SciPy on ARX + d_hat)
                    │
                    ▼ u [kW]
              CasADi heater plant ──► temperature [°C]
                    ▲
         PID + optimized PID (same plant, same metrics)
```

Details: [`HOW-IT-WORKS.md`](HOW-IT-WORKS.md) · Course write-up: [`report/report.md`](report/report.md)

Educational use. Licences: [`CREDITS.md`](CREDITS.md).
