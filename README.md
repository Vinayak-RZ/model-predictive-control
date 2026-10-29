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

Three scripted scenarios, a **multipage Streamlit lab**, batch plots under `results/`, and a **78 s showcase video** driven by the same simulation exports.

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

| Playground | Step-through MPC | Scorecard |
| --- | --- | --- |
| ![Playground](docs/streamlit-playground.png) | ![Step-through](docs/streamlit-step-through.png) | ![Scorecard](docs/streamlit-scorecard.png) |

- **Playground** — sliders for setpoint, disturbance, noise, PID gains, MPC horizon/weight; one-click presets; MPC solve time per step.
- **Step-through** — prev/next through MPC predictions and the first applied move.
- **Scorecard** — IAE, overshoot, settling, energy, violations for all three controllers (includes an honest **model mismatch** row).

Theme: `.streamlit/config.toml` (projector-friendly, single accent `#2563eb`).

## Showcase video

[![Video poster](docs/video-poster.png)](video/out/mpc-vs-pid.mp4)

**File:** [`video/out/mpc-vs-pid.mp4`](video/out/mpc-vs-pid.mp4) · **Duration:** 78 s · **Size:** ~1.4 MB · **Source:** [`video/index.html`](video/index.html) (HyperFrames) + [`video/data/`](video/data/) JSON from `python3 scripts/export_video_data.py`.

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
