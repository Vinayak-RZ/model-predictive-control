# Sanitisation log

Source: `Stamped-Energy/stamped` @ `0f77288562f4274c39005e922e3c41f8ca0ad5d1`
(`integration/build-2026-10-28`).

## Copied (logic unchanged)

- `cells/process/src/stamped_process/control/mpc.py`
- `cells/process/src/stamped_process/control/identified.py`
- `cells/process/src/stamped_process/control/model_card.py`
- `cells/process/src/stamped_process/twin/ibh.py`
- `cells/process/src/stamped_process/twin/codegen.py`

Import paths were rewritten from `stamped_process.*` to `mpc_from_stamped.*`
so the package runs standalone. The MPC mathematics and IBH formula were not
changed (MPC work is frozen in the product).

## Included in slim form

- `thresholds.py`: only the `SetpointLimits` dataclass that `mpc.solve`
  needs. The product readers that pull limits from a line pack (and depend on
  `stamped_contracts`) were left out.

## Not copied (on purpose)

- `control/runner.py` and module wiring (needs contracts, Temporal, store)
- `control/residual_rl.py` and shield (separate residual RL path)
- `control/deploy_gate.py`, `fit_quality.py`, `plant_headroom.py`,
  `shadow_read.py`, `no_worse.py`, tool-life / cycle-time modules
- `twin/predict.py` (needs line-pack contracts)
- Product `twin-runtime/` C++ tree (box runtime); codegen can still emit C
- Secrets, credentials, env files, API keys (none were present in these sources)
- Customer or plant names, real plant data, client-specific parameters, pricing
  (none were present in these sources; product already refuses to bake plant
  numbers into the twin)

## Replaced / labelled illustrative

- Unit-test and demo ARX coefficients `a=0.9`, `b=0.05`, windows
  `[900, 1100]`, `max_step=50`, and IBH fixture params
  (`m_kg=2`, `c_p=500`, `eta=0.5`, `U=10`, `T_amb=25`) are the same
  **test-only** values from the product tests, already marked as not plant
  data.
- Model-card docstring no longer points at a private `stamped-external`
  design path.

## Still sensitive (judgement)

- The **control structure itself** (offset-free SISO MPC on an identified
  linear model, SciPy L-BFGS-B, integrating disturbance per Pannocchia and
  Rawlings 2003, and the IBH heat-balance twin authored in CasADi) is product
  IP. The owner authorised copying it into a public course repository.
- Generated C still uses the `stamped_ibh_step` / `stamped/` include names
  from the product ABI. Rename if you want the course tree to avoid the
  product symbol prefix.
