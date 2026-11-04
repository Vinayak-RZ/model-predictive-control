# Academic report (Industrial Control)

Course write-up for the offset-free MPC vs PID lab on the induction-heater twin.

| Artifact | Path |
| --- | --- |
| LaTeX source | [`main.tex`](main.tex) |
| Built PDF | [`report.pdf`](report.pdf) |
| Figures | [`figures/`](figures/) |
| Metrics used in the PDF | [`metrics_summary.json`](metrics_summary.json) |
| Shorter Markdown draft | [`report.md`](report.md) (numbers may lag the PDF; rebuild metrics then edit) |

British spelling. Prefer numbers from `metrics_summary.json` after a metrics rebuild. The current PDF is a coursework layout pass with **12 figures** (README MPC infographic, architecture, three Streamlit screens, IAE bars, four scenario traces, violations, robustness); ambient-step metrics stay in the summary table only.

## What the numbers mean

- **Batch scenarios** in `metrics_summary.json → scenarios`: setpoint tracking, disturbance rejection, power constraints, model mismatch, ambient step, plus a robustness check that reuses nominal-tuned PID gains under mismatch.
- **MPC params** under `mpc_params_retuned`: `N=40` (45 on the power scenario), `Nu=1`, `Qt=50`, `R=0`, observer gain `1.0`, **reference preview** on. Legacy comparison (`mpc_params_legacy`, `legacy_vs_retuned_setpoint_iae`) is the pre-retune `N=25`, no preview, `Qt=0` run.
- **UI / README proof table** should match the retuned settling times and limit hits from this JSON after a metrics rebuild. Streamlit still freezes optimised-PID gains from the mild setpoint case for the fair UI comparison; batch scripts retune per scenario for the report tables.
- Simulation PNGs under `figures/<scenario>.png` are produced by the metrics script. Architecture / bar charts (`architecture.png`, `iae_bars.png`, …) come from the charts script. Streamlit screenshots come from `docs/` at report freeze time. The opening MPC loop figure is a whitened copy of `assets/mpc-infographic.png`. Video poster / animation preview frames are **not** included in the PDF.

## Rebuild from the repo root

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Full pipeline: metrics → charts → PDF
bash scripts/rebuild_academic_report.sh
```

Or step by step:

```bash
python3 scripts/rebuild_report_metrics.py   # writes report/metrics_summary.json + figures/<scenario>.png
python3 scripts/rebuild_report_charts.py    # architecture + summary bars
cd report
latexmk -pdf -interaction=nonstopmode main.tex   # preferred
# else: pdflatex main.tex && pdflatex main.tex
# else: tectonic main.tex
cp -f main.pdf report.pdf
```

Dependencies: Python 3.12+, project `[dev]` extras (matplotlib, pytest, streamlit), and a LaTeX engine (`latexmk`, `pdflatex`, or `tectonic`). CasADi and SciPy come from the core install.

A full metrics rebuild takes a few minutes (PID retunes per scenario). Do not hand-edit numbers in `main.tex`; change the sim / knobs, rebuild metrics, then update any hard-coded table cells in the TeX to match the JSON.

## Layout of `main.tex`

Abstract → MPC loop infographic → introduction → plant and identification → offset-free MPC (with preview / terminal cost) → PID baselines → experiments → results (MPC-best cells in blue bold) → discussion of losses → conclusion → references.
