# MPC from Stamped (course extract)

Standalone copy of Stamped's offset-free model predictive control (MPC) and
the CasADi induction billet heater (IBH) heat-balance twin, prepared for an
Industrial Control coursework repository.

**Source:** `Stamped-Energy/stamped` branch `integration/build-2026-10-28` at
commit `0f77288562f4274c39005e922e3c41f8ca0ad5d1`.

## What is in here

| Path | Role |
| --- | --- |
| `src/mpc_from_stamped/mpc.py` | Offset-free MPC solver (SciPy L-BFGS-B) |
| `src/mpc_from_stamped/identified.py` | Identified discrete linear plant model |
| `src/mpc_from_stamped/thresholds.py` | Setpoint window and max-step limits |
| `src/mpc_from_stamped/model_card.py` | Model-card gate used before MPC may run |
| `src/mpc_from_stamped/twin/ibh.py` | CasADi IBH heat-balance twin |
| `src/mpc_from_stamped/twin/codegen.py` | Emit matching C for the twin step |
| `examples/run_mpc_demo.py` | Illustrative closed-loop demo |
| `HOW-IT-WORKS.md` | Plant model, cost, constraints, solver, horizons, tuning |
| `SANITISED.md` | What was removed or replaced for public use |

## Important accuracy note

The **MPC quadratic programme uses SciPy**, not CasADi. CasADi is used to
**author the IBH plant twin** (heat-balance step). Both pieces come from the
same Stamped process cell and are included here.

CasADi 3.8.2 is LGPL-licensed. This tree does **not** vendor CasADi; install
it from PyPI (see `requirements.txt`).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# or: pip install -r requirements.txt && pip install -e .
```

## Run

```bash
pytest
python examples/run_mpc_demo.py
```

## Licence note

Stamped product code in this extract was copied with the owner's permission
for a public course repository. CasADi remains a separate LGPL dependency.
