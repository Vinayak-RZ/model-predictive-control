# How the MPC and IBH twin work

British spelling. Numbers below are taken from the source or from illustrative
unit tests; nothing here invents a plant value.

## Big picture

There are two related pieces:

1. **Offset-free MPC** (`mpc.py`) on an **identified discrete linear model**.
   The quadratic programme is solved with **SciPy** (`scipy.optimize.minimize`,
   method `L-BFGS-B`).
2. **Induction billet heater (IBH) twin** (`twin/ibh.py`), authored with
   **CasADi**. This is the physics heat-balance step used as a simulation
   plant. It is not the QP solver.

## Plant model (for the MPC)

The MPC predicts with a SISO discrete linear model
(`IdentifiedLinearModel` in `identified.py`):

```text
y[k+1] = a * y[k] + b * u[k] + d_hat
```

- `a`, `b`, `dt_s`, `n_samples`, `residual_rms`, and `experiment` come from an
  identification experiment. The module never invents them.
- `b` must be non-zero; `dt_s` must be positive; `n_samples` must be at least 3.
- In the unit tests the illustrative ARX is `a = 0.9`, `b = 0.05`, `dt_s = 1.0`
  (steady-state gain `b / (1 - a) = 0.5`). Those are test-only values, not
  plant numbers.

Offset-free behaviour uses an integrating disturbance `d_hat`
(Pannocchia and Rawlings, 2003), refreshed each run from the one-step
innovation (`refresh_disturbance`):

- First run (no previous `y` or `u`):  
  `d0 = (1 - a) * y_meas - b * u_current`
- Later runs:  
  `y_pred = a * last_y + b * last_u + d_hat`, then  
  `d_hat ← d_hat + (y_meas - y_pred)`

## Cost function

For a candidate held input `u` over the horizon, the predictor rolls

```text
y ← a * y + b * u + d_hat
```

for `horizon_steps` steps. The cost is the sum of squared tracking errors:

```text
J(u) = sum_i (y_i - y_ref)^2
```

There is **no move-weight term** in this coursework controller. The module
docstring states that explicitly so that nothing is invented.

Decision variables: a **single** held input for the whole horizon (one degree
of freedom for this SISO implementation).

## Constraints

From `SetpointLimits` and the current input `u0`:

- Window: `low <= u <= high`
- Rate: `|u - u0| <= max_step`
- Combined box passed to the solver:  
  `lo = max(low, u0 - max_step)`, `hi = min(high, u0 + max_step)`
- If `lo > hi`, the solver raises (no feasible setting within one step).

Active constraints reported after the solve:

- `{setpoint_id}.window` if `u_star` sits on `low` or `high`
- `{setpoint_id}.max_step` if `|u_star - u0|` equals `max_step`

Illustrative test window: `low = 900`, `high = 1100`, `max_step = 50`, unit
`kW`, setpoint id `power_setpoint`.

## Solver

- Library: SciPy
- Method: `L-BFGS-B` with bounds `[(lo, hi)]`
- Initial guess: current `u0` clipped into `[lo, hi]`
- Wall-clock limit: `time_limit_s`. The objective checks `time.monotonic()`
  and raises `MpcTimedOut` if the deadline passes.
- Returns the **first-move** proposal (the held `u_star`), the reference,
  `d_hat`, the predicted `y` sequence, active constraints, and the updated
  `MpcState`.

Horizon and solver time limit are required function arguments.

## Prediction and control horizons

The prediction horizon is `horizon_steps`. The control move is a single held
value for that whole horizon (control horizon effectively one block of length
`horizon_steps`).

Illustrative values used in tests and the demo:

- `horizon_steps = 20` in the core solve test and demo loop
- `solver_time_limit_s = 2.0` in those same places

`horizon_steps` must be an integer at least 1.

## Tuning (what the code exposes)

| Knob | Where | Notes |
| --- | --- | --- |
| `a`, `b`, `dt_s` | `IdentifiedLinearModel` | From identification; refused if `b == 0` |
| `horizon_steps` | `solve(...)` | Positive integer |
| `solver_time_limit_s` | `solve(...)` | Soft deadline via `MpcTimedOut` |
| `low`, `high`, `max_step` | `SetpointLimits` | Passed in by caller |
| `y_ref` | `solve(...)` | Controlled-variable reference |
| Model card | `model_card.py` | Optional gate: held-out residual under `max_held_out_rms`, `b != 0` |

There is no move suppression weight and no separate observer gain: the
disturbance update is a full innovation correction.

## CasADi plant twin (IBH)

Separate from the QP. The heat balance is

```text
m * c_p * dT/dt = eta * P_coil - U * (T - T_amb)
```

Explicit Euler step in CasADi (`ibh_step_function` / `step_ibh`):

```text
T_next = T + dt * (eta * P - U * (T - T_amb)) / (m * c_p)
```

Parameter names (all must be set; no defaults): `m_kg`, `c_p_j_per_kg_k`,
`eta`, `U_w_per_k`, `T_amb_c`.

Illustrative fixture used in tests (not plant defaults):
`m_kg = 2.0`, `c_p_j_per_kg_k = 500.0`, `eta = 0.5`, `U_w_per_k = 10.0`,
`T_amb_c = 25.0`. With `T = 25`, `P = 1000`, `dt = 1` the step gives
`T_next = 25.5`.

`codegen.py` can emit a matching C function `ibh_step` and header guard
`IBH_STEP_H` under `include/ibh/` for embedded runtimes. CasADi itself is not
vendored; install `casadi==3.8.2` from PyPI (LGPL-3.0).

## How to run

```bash
pip install -r requirements.txt && pip install -e .
pytest
python examples/run_mpc_demo.py
python examples/run_simulations.py
streamlit run app.py
```

The demo drives the illustrative ARX with the offset-free solver for a few
steps, then runs one CasADi IBH twin step with the fixture parameters above.
Simulations write comparison plots to `results/`.
