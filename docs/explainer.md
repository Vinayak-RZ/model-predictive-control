# What this project is doing (plain explainer)

> **Companion:** maths and industrial-control detail → [THEORY.md](THEORY.md)  
> Short engineering reference → [HOW-IT-WORKS.md](../HOW-IT-WORKS.md) · Results narrative → [report/report.md](../report/report.md)

All numbers in this lab are **illustrative coursework values**, not a real customer plant.

---

## In one sentence

Every second, the controller looks a short way into the future with a model of the heater, tries candidate coil-power plans that respect power limits, picks the plan whose predicted temperature stays closest to the target, applies **only the first step** of that plan, then measures the real temperature and does it again.

## The picture to hold

You are driving toward a destination on a winding road (the temperature you want). A normal thermostat only reacts when you are already too hot or too cold. This controller is like glancing at a map for the next few bends: it imagines “if I set the heater power like *this*, where will temperature be in the next half-minute?”, refuses plans that would demand illegal power, then turns the wheel once and looks again.

That look-ahead loop is what people call **model predictive control** (MPC).

---

## The four boxes on the infographic

The repo banner diagram is the same story in engineering boxes. Walk them in the order the controller thinks.

### 1. Optimisation (the decision box)

**What it does:** scores many candidate power plans and picks the best one that still obeys the rules.

**Rules here:** coil power must stay inside a allowed window, and it cannot jump by more than a maximum step from the current power. The “score” is how far the *predicted* temperature would sit from the temperature you asked for (the **setpoint**), over a short future window called the **horizon**.

**In this project:** SciPy’s `L-BFGS-B` optimiser does that search inside [`src/mpc_core/mpc.py`](../src/mpc_core/mpc.py). It does **not** talk to the real heater directly — it only talks to the simulation model below.

### 2. Simulation model (the imagination)

**What it does:** answers “if I apply this power sequence, what temperature trajectory do I get?”

**Important split in this lab:**

| Piece | Role | Code |
| --- | --- | --- |
| **MPC simulation model** | Fast linear guess used *inside* the optimiser | Identified model in `identified.py`, rolled forward in `mpc.py` |
| **Plant / heater twin** | Stand-in for the *real* heater in closed-loop demos | Nonlinear heat-balance step in `twin/ibh.py` |

The optimiser plans with the linear model. The demo then applies power to the nonlinear twin (plus optional noise and disturbances). That mismatch is intentional — industrial controllers rarely get a perfect model.

### 3. Input prediction (planned power over the horizon)

**What it is:** a sequence of future coil-power values the optimiser is considering, from “now” out to the end of the horizon.

By default this lab uses a simple plan shape: a small number of free power moves (often **one**), then hold the last value for the rest of the horizon. Only the **first** planned power is sent to the plant. The rest of the sequence is discarded and recomputed next sample. That discard-and-replan habit is the **receding horizon**.

### 4. State prediction (planned temperature over the horizon)

**What it is:** the temperature trajectory the simulation model expects if that input plan were followed.

The optimiser keeps adjusting the input plan until the state prediction hugs the setpoint as well as the constraints allow. Those prediction charts are what the Streamlit **Step-through** page shows for one MPC tick.

```mermaid
flowchart TB
  setpoint[Setpoint]
  subgraph mpc [Model_predictive_controller]
    opt[Optimisation]
    simModel[Simulation_model]
    inputPred[Input_prediction]
    statePred[State_prediction]
    opt --> inputPred
    inputPred --> simModel
    simModel --> statePred
    statePred --> opt
  end
  plant[Heater_plant]
  disturbance[Disturbance]
  setpoint --> opt
  plant -->|"measured_temperature"| opt
  opt -->|"first_power_move"| plant
  disturbance --> plant
```

---

## The loop that never stops

One control tick, in order:

1. **Measure** the current temperature (and know the current power).
2. **Update a disturbance guess** so slow model error and load changes do not leave a permanent offset (this lab’s “offset-free” piece).
3. **Propose** candidate power plans that respect window and rate limits.
4. **Predict** temperature for each plan with the linear model.
5. **Choose** the plan with the best score.
6. **Apply** only the first power of that plan to the plant.
7. Wait one sample time, then go back to step 1.

```mermaid
flowchart LR
  measure[Measure] --> correct[Correct_disturbance]
  correct --> propose[Propose_plans]
  propose --> predict[Predict_temperature]
  predict --> choose[Choose_best]
  choose --> apply[Apply_first_move]
  apply --> measure
```

---

## What this repository actually wires together

```mermaid
flowchart TB
  scenario[Scenario_setpoint_and_events]
  subgraph controllers [Controllers]
    mpcCtrl[MPC]
    pidCtrl[PID]
    optPid[Optimised_PID_gains]
  end
  plantTwin[CasADi_heater_twin]
  metrics[Metrics_and_plots]
  scenario --> mpcCtrl
  scenario --> pidCtrl
  optPid --> pidCtrl
  mpcCtrl -->|"power"| plantTwin
  pidCtrl -->|"power"| plantTwin
  plantTwin -->|"temperature"| mpcCtrl
  plantTwin -->|"temperature"| pidCtrl
  plantTwin --> metrics
```

- **Closed-loop runner:** [`src/mpc_core/sim/simulate.py`](../src/mpc_core/sim/simulate.py) — same plant, noise options, and limits for fair comparison.
- **Interactive lab:** `streamlit run app.py` — Playground, Step-through, Scorecard.
- **Batch figures:** `examples/run_simulations.py` → `results/`.

You can run three controller stories on the same heater story:

| Controller | Behaviour in one line |
| --- | --- |
| **MPC** | Plans ahead with a model; hard power limits inside the optimiser |
| **PID** | Reacts to the temperature error now / over time / how fast it is changing; no preview |
| **Optimised PID** | Still a PID online, but its three gains were chosen offline by an optimiser on the same scenario |
| **Optimised PID + FF** | Same optimiser, plus the **same** measured `T_amb`/`U` static feedforward MPC uses (`pid_measured_feedforward=True`) |

---

## PID, without the mystique

A **PID** controller does not invent future plans. Each sample it looks at the **error** (setpoint minus measured temperature) and builds a power command from three pieces:

- **P (proportional):** how far off you are *right now* — big gap, bigger nudge.
- **I (integral):** how long you have been a bit off — closes the last stubborn gap.
- **D (derivative):** how fast the error is changing — brakes before you overshoot.

In this lab, [`src/mpc_core/sim/pid.py`](../src/mpc_core/sim/pid.py) also **clips** power to limits and uses **anti-windup** so the integral does not keep winding up while the heater is already at max power.

### Optimised PID

Hand-picked gains are one baseline. **Optimised PID** keeps the same online law, but [`src/mpc_core/sim/pid_tune.py`](../src/mpc_core/sim/pid_tune.py) searches for gains that minimise a cost: mainly **IAE** (integrated absolute error) plus a penalty if the run violates power or rate limits.

So “optimised PID” means *offline tuning by optimisation*, not a second predictive controller. It is a strong baseline: gains are searched per scenario on the same plant and limits. After the Nov 2026 MPC retune (Kalman observer + measured ambient/\(U\) feedforward), **MPC leads on every batch IAE row** in `results/metrics_summary.json`, while PID still has no horizon preview.

---

## Explain it to a friend

Use this script almost verbatim:

> We built a small induction-heater lab in software. The “real” heater is a heat-balance twin: power in, heat loss out, temperature moves.  
> Against that twin we run three controllers. A PID turns the power up or down from the temperature error. An optimised PID is the same idea with gains found by a search.  
> MPC is different: every second it uses a simple model to predict temperature under candidate power plans, refuses illegal plans, picks the best one, applies only the first power setting, then remeasures and replans.  
> The point of the coursework is to see when preview and hard constraints help, and when a well-tuned PID still competes.

---

## Where the picture breaks

- The **map** (linear model) is not the **road** (nonlinear twin). Bad models shrink MPC’s advantage — the lab has a model-mismatch scenario for that.
- Default MPC plans are deliberately simple (few free moves, then hold). Full industrial MPC can free every step and add move penalties; this coursework keeps the decision small.
- We constrain **power**, not temperature. A plant that must never exceed a metal temperature limit would need extra constraint machinery.
- Parameters and gains are coursework illustrations. Do not treat plots as a site acceptance test.

---

## Words introduced here

| Word | Meaning in this project |
| --- | --- |
| **Setpoint** | The temperature you want |
| **Horizon** | How far into the future the MPC predicts and scores |
| **Receding horizon** | Replan every sample; apply only the first move |
| **Plant** | The process being controlled (here: heater twin) |
| **Simulation model** | The predictor inside the MPC optimiser |
| **Input prediction** | Planned future power sequence |
| **State prediction** | Predicted future temperature sequence |
| **Constraint** | Hard rule the optimiser must not break (power window, max step) |
| **Offset-free** | Disturbance correction so steady error does not stick around |
| **PID** | Proportional–integral–derivative error feedback |
| **IAE** | Integrated absolute tracking error (smaller is tighter tracking) |

---

## Where to go next

- **Maths, heat balance, cost function, discrete PID, metrics:** [THEORY.md](THEORY.md)
- **MPC papers mapped to code:** [mpc_literature.md](mpc_literature.md)
- **Knob list and solver notes:** [HOW-IT-WORKS.md](../HOW-IT-WORKS.md)
- **Scenario tables and figures:** [report/report.md](../report/report.md)

---

## Design choices (for the owner)

| Choice | What we picked | Why |
| --- | --- | --- |
| Language | Python 3.12 | Matches course stack, SciPy/CasADi bindings, Streamlit UI |
| Plant | CasADi heat balance `ηP − U(T−T_amb)` | Transparent physics, same twin in sim and report |
| MPC model | Identified ARX `y_{k+1}=ay_k+bu_k` | Fast roll-out inside the optimiser; coeffs from an offline step test |
| Solver | SciPy `minimize` (L-BFGS-B / SLSQP) | Small SISO QP-like problem; no external MILP licence |
| Horizon | `N=40` (45 on power limits) | Long enough to see setpoint steps and saturation before they hit |
| Weights | `Q=1`, `Q_t=50`, `R=0` | Preview + terminal cost improved setpoint IAE; move penalty trials hurt on this slow plant |
| Observer | Kalman gain ≈ **2** on `d̂` | Faster bias tracking after heat-loss / ambient events (see literature note) |
| Feedforward | Measured `T_amb`, `U` in prediction | Maps known load change to extra power before feedback alone catches up |
| PID | Position form + anti-windup | Standard teaching baseline; same limits as MPC |
| Optimised PID | SciPy L-BFGS-B per scenario | Fair strong baseline—not handicapped when MPC improved |

---

## Maths walkthrough (step by step)

### 1. Continuous heater (plant truth)

\[
m c_p \frac{dT}{dt} = \eta P_{\mathrm{coil}} - U\,(T - T_{\mathrm{amb}})
\]

Discretised with explicit Euler at `dt = 1 s` in `twin/ibh.py`.

### 2. MPC prediction model

\[
y_{k+1} = a\,y_k + b\,(u_k + u_{\mathrm{ff},k}) + \hat d_k
\]

- \((a,b)\) from least squares on a nominal power step.
- \(\hat d_k\) is an **integrating bias** updated from measurement innovation (offset-free MPC).
- \(u_{\mathrm{ff},k}\) compensates measured changes in \(T_{\mathrm{amb}}\) and \(U\) at the current temperature.

### 3. Cost and constraints (each sample)

Minimise over future power moves \(u_0,\ldots,u_{N_u-1}\) (held to horizon):

\[
J = \sum_{i=0}^{N-1} Q\,(y_i - r_i)^2 + Q_t\,(y_N - r_N)^2
\]

Subject to power window and slew: \(|u_k - u_{k-1}| \le \Delta u_{\max}\).

Only **the first** optimised power is applied; then the window shifts (**receding horizon**).

### 4. Observer update

\[
\hat d_k \leftarrow \hat d_{k-1} + L\,(y_k^{\mathrm{meas}} - \hat y_k), \quad L \approx 2
\]

Tuned as a scalar Kalman gain for the bias state (`kalman_disturbance_observer_gain`).

### 5. PID (comparison)

\[
u_k = K_p e_k + K_i \sum e + K_d \frac{e_k - e_{k-1}}{\Delta t}, \quad e = r - y^{\mathrm{meas}}
\]

Optimised gains minimise IAE + violation penalty on the **same** plant (`pid_tune.py`).

---

## Why MPC wins here (mechanically)

1. **Preview:** It sees the 80→120 °C step (or 165 °C target) before the error grows; PID waits for drift.
2. **Constraints in the optimiser:** Under 150 kW / 8 kW/s, MPC never plans illegal moves; hand-tuned PID logs six slew violations.
3. **Bias + feedforward:** Heat-loss and ambient steps enter the prediction through \(u_{\mathrm{ff}}\) and a fast \(\hat d\); PID must infer load only from temperature error (unless retuned offline).
4. **One policy everywhere:** Batch MPC uses the same knobs on all scenarios; optimised PID gets fresh gains per scenario. After adding **optimised PID + the same feedforward**, MPC still has the lowest IAE on every primary scenario (see README table).

---

## Limitations (honest)

- **Tuning exposure:** Horizon \(N\), terminal weight, and Kalman observer gain were chosen while inspecting these batch scenarios. Held-out checks (20 noise seeds, unseen step timings, ±20% plant scales) still show MPC with the **lowest IAE on every run** in those sweeps—see `results/held_out_validation.json`—but this is not a guarantee on real plant data.
- **Feedforward symmetry:** MPC and **Opt. PID+FF** both use measured `T_amb` and `U`. Plain PID and optimised PID without FF do not. On the **ambient step**, retuned Opt. PID+FF (**585** IAE) is slightly **worse** than optimised PID alone (**578**) because the static offset fights the retuned feedback gains.
- **Model class:** Prediction stays a single ARX plus bias; no MIMO, no state constraints on metal temperature, no move blocking beyond one held move.
- **Compute:** Each sample solves a small NLP; PID is cheaper online.
- **Energy:** Hand-tuned PID sometimes uses less energy by violating slew limits (six steps on the power-limit case).

---

## Two-minute pitch

> We built a software induction heater and three controllers on top. PID chases temperature error. Optimised PID picks gains by search but still has no lookahead. MPC every second rolls a simple model forward, respects power limits, updates a disturbance estimate, and applies one planned move. On our coursework scenarios MPC now has the lowest integrated error on setpoint changes, disturbances, ambient shifts, tight power limits, and model mismatch—while keeping the coil inside legal power and slew. That is the industrial point: plan with constraints, reject loads without retuning every time the door opens.

---

## Demo script (Streamlit or batch)

Run `streamlit run app.py` or `python3 examples/run_simulations.py`. Walk scenarios in this order:

1. **Setpoint tracking** — Watch MPC begin raising power before 30 s because preview sees the upcoming 120 °C target; compare settling vs PID.
2. **Disturbance rejection** — At 70 s, heat loss jumps; MPC feedforward + \(\hat d\) recover before optimised PID’s retuned gains finish integrating error.
3. **Ambient step** — Same timing, ambient rises 8 °C; MPC trims power via negative feedforward while holding 115 °C.
4. **Power limits** — Target 165 °C with 150 kW cap; MPC saturates smoothly at zero violations; note PID violation count on the scorecard.
5. **Model mismatch** — Plant parameters drift; MPC bias absorbs much of the gap; frozen optimised-PID gains degrade (robustness figure in the PDF).

On **Step-through**, pause one MPC tick: read predicted temperature curve, planned power, and active constraints caption.

---

## Words introduced here
