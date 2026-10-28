# Model predictive control — induction billet heater

Course project for **Industrial Control**, IIT Roorkee (Electrical Engineering,
Vinayak). This repository implements **offset-free model predictive control**
(SciPy L-BFGS-B) and a **CasADi heat-balance twin** of an induction billet
heater (IBH), with closed-loop simulations, a Streamlit teaching UI, and a
short written report.

## Highlights

- **Three scenarios:** setpoint tracking, disturbance rejection (heat-loss step),
  tight power/rate limits — MPC vs tuned PID with IAE/ISE, overshoot, settling
  time, violations, and energy.
- **`app.py`:** side-by-side runs with plain-language MPC explanations.
- **`report/report.md`:** course write-up with figures from `results/`.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate   # when venv is available
pip install -r requirements.txt
pip install -e .
pytest
python examples/run_simulations.py    # writes PNGs to results/
streamlit run app.py
```

If `venv` is unavailable: `pip install --user -r requirements.txt` and
`python3 -m streamlit run app.py` (add `~/.local/bin` to `PATH`).

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/mpc_core/mpc.py` | Offset-free MPC solver |
| `src/mpc_core/twin/ibh.py` | CasADi IBH twin step |
| `src/mpc_core/sim/` | Closed-loop simulation, metrics, plotting |
| `examples/run_mpc_demo.py` | Minimal MPC + one IBH step |
| `examples/run_simulations.py` | Batch MPC vs PID → `results/*.png` |
| `app.py` | Streamlit interactive demo |
| `report/report.md` | Course report |
| `results/` | Simulation plots and `metrics_summary.json` |
| `CREDITS.md` | Third-party licences and references |
| `HOW-IT-WORKS.md` | Plant model, cost, constraints, solver |

## Screenshot (Streamlit UI)

![Streamlit UI](docs/app_screenshot.png)

## Solver note

The MPC quadratic program uses **SciPy**, not CasADi. CasADi authors the **plant
twin** only. CasADi 3.8.2 is **LGPL-3.0** and is installed from PyPI — not
vendored in this tree.

## Licence

See `CREDITS.md` for dependency licences. Course simulation code is provided
for educational use.
