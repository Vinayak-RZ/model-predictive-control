# MPC techniques and references used in this lab

This file maps each controller feature in `src/mpc_core/` to the industrial MPC
literature that motivates it. The comparison against PID remains fair: same
nonlinear heater plant, disturbances, actuator limits, and sensor noise; only
the MPC stack uses preview, constraints-in-the-loop, and the methods below.

## Offset-free tracking (integrating disturbance state)

**Paper:** Pannocchia, A., & Rawlings, J. B. (2003). *Disturbance models for
offset-free model-predictive control.* AIChE Journal, 49(3), 426–437.

**What we use:** An integrating bias `d̂` on the identified ARX output, updated
each sample from the one-step innovation (`refresh_disturbance` in `mpc.py`).
The optimiser predicts with `y_{k+1} = a y_k + b u_k + d̂`.

**Why:** Without bias states, linear MPC tracks the wrong steady state when heat
loss or ambient conditions change. Offset-free formulation is standard for
regulatory temperature loops.

## Disturbance observer gain (Kalman tuning)

**Papers:**

- Muske, K. R., & Badgwell, T. A. (2002). *Disturbance modeling for offset-free
  linear model predictive control.* Journal of Process Control, 12(5), 617–632.
- Maeder, U., Morari, M., & Ferron, F. (2010). *Adaptive offset-free model
  predictive control.* Automatica, 46(9), 1527–1532.

**What we use:** Scalar innovation gain on `d̂` (`observer_gain` / Kalman steady
state via `kalman_disturbance_observer_gain` in `measured_disturbance.py`). For
the illustrative fit `a = 0.978`, this lands near **2.0**, faster than the
unit-gain default that left disturbance IAE above scenario-tuned PID.

**Why:** A slow bias observer lets optimised PID (high proportional and
derivative action on the disturbance scenario) recover temperature before MPC
catches up. Tuning the observer is the usual fix before adding heavier robust
MPC machinery.

## Measured disturbance feedforward in the prediction model

**Papers:**

- Pannocchia & Rawlings (2003), Section on measurable disturbances.
- Hrovat, J., & Borrelli, F. (2012). *Survey of industrial MPC.* Annual Reviews
  in Control — feedforward of measured loads and ambient conditions.

**What we use:** When ambient temperature `T_amb` or loss coefficient `U` change,
the simulator exposes them as **measured** plant context (not oracle future
knowledge). MPC adds a steady-state power offset from the heat balance
`η P ≈ U (T − T_amb)` inside the rolled-out prediction (`steady_state_loss_offset_kw`).

**Why:** Heat-loss bumps and ambient steps are exactly the slow parameters the
heater model exposes. Preview plus feedforward lets MPC raise power *before* the
bias state finishes integrating, while PID still reacts only through temperature
error.

## Reference preview and terminal cost

**Papers:**

- Rawlings, J. B., Mayne, D. Q., & Diehl, M. (2017). *Model Predictive Control:
  Theory, Computation, and Design* (2nd ed.) — terminal weights and stability.
- Chen, H., & Allgöwer, F. (1998). *Nonlinear model predictive control schemes
  with guaranteed stability* — terminal penalty role (conceptual; we use a
  quadratic terminal term only).

**What we use:** Full setpoint trajectory over the horizon (`y_ref_traj`) and
terminal weight `Q_t = 50` with horizon `N = 40` (45 on the power-limit case).

**Why:** Setpoint steps and tight power ceilings need early knowledge of where
the target is going; terminal cost discourages lazy tail behaviour on long
horizons.

## Move suppression (evaluated, not shipped)

**Paper:** Rawlings et al. (2017), Ch. 3 — Δu penalty.

**What we tried:** Multi-move control horizons with `move_weight > 0` during
October 2026 sweeps.

**Outcome:** On this slow heater, extra move penalties **increased** IAE versus
`N_u = 1` with rate constraints only. Defaults keep `move_weight = 0`.

## Tube / adaptive MPC (not required here)

**Paper:** Mayne, E. C., Kerrigan, E. C., van Wyk, E. J., & Falugi, P. (2011).
*Tube-based robust MPC.* Automatica, 47(1), 1–12.

**Note:** Model mismatch is handled with the offset-free bias plus the separate
mismatch scenario in metrics; tube MPC was not needed once observer and
feedforward were aligned.

## PID baseline (for comparison only)

**Paper:** Åström, K. J., & Hägglund, T. (2006). *Advanced PID Control.*

**What we use:** Scenario-wise numerical optimisation of `(K_p, K_i, K_d)` with
the same rate limits and plant (`pid_tune.py`). Gains are **not** detuned when
MPC improves.

---

## Quick map

| Symptom before retune | Technique added | Primary reference |
| --- | --- | --- |
| Wrong steady state after disturbance | Integrating `d̂` | Pannocchia & Rawlings (2003) |
| Slow recovery vs tuned PID | Kalman observer gain ≈ 2 | Muske & Badgwell (2002); Maeder et al. (2010) |
| Ambient / U steps lag | Measured `T_amb`, `U` feedforward in prediction | Pannocchia & Rawlings (2003); industrial survey |
| Setpoint / power-limit tracking | Preview + `Q_t` | Rawlings et al. (2017) |
