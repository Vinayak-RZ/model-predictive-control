# Model predictive control for induction heating

**Author:** Vinayak · Industrial Control coursework · IIT Roorkee (Electrical Engineering)

> Canonical PDF: [`report.pdf`](report.pdf) from [`main.tex`](main.tex). Rebuild: see [`README.md`](../README.md). Numbers below match `metrics_summary.json` after the Nov 2026 disturbance retune.

## Abstract

This report compares **offset-free model predictive control (MPC)** against a
**tuned discrete PID** baseline on a CasADi heat-balance model of an induction
heater. Scenarios cover setpoint tracking, disturbance rejection, constrained
power, model mismatch, and an ambient step. After reference preview, terminal
cost, Kalman-tuned disturbance estimation, and measured ambient/\(U\)
feedforward, MPC posts the **lowest IAE on every scenario** while keeping zero
power violations wherever limits bind.

All parameters are **illustrative coursework values**, not customer or plant data.

---

## Summary metrics (MPC vs optimised PID)

| Scenario | MPC IAE | Optimised PID IAE | MPC wins IAE? |
| --- | ---: | ---: | --- |
| Setpoint tracking | **869** | 1466 | yes |
| Disturbance rejection | **466** | 586 | yes |
| Ambient step | **416** | 578 | yes |
| Power limits | **8735** | 9033 | yes |
| Model mismatch | **1088** | 1667 | yes |

Literature map: [`docs/mpc_literature.md`](../docs/mpc_literature.md). Plain-language walkthrough: [`docs/explainer.md`](../docs/explainer.md).

---

## What changed in the disturbance retune

Previously, a unit innovation gain on \(\hat{d}\) left MPC slightly above
scenario-tuned PID on heat-loss and ambient IAE. The fix (cited in
`mpc_literature.md`):

1. **Kalman-tuned observer gain** (\(\approx 2.0\) on the illustrative ARX).
2. **Measured \(T_{\mathrm{amb}}\) and \(U\)** feedforward inside the prediction roll-out.

PID baselines were **not** detuned; optimised gains are still from `pid_tune.py` on each scenario.

---

## Rebuild

```bash
python3 scripts/rebuild_report_metrics.py
python3 scripts/rebuild_report_charts.py
bash scripts/rebuild_academic_report.sh
```

Figures land in `report/figures/` and `results/`.
