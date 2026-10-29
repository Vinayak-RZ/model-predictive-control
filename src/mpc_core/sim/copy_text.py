"""User-facing UI strings (drafted for write-like-vinayak). Do not polish casually."""

from __future__ import annotations

SIDEBAR_BRAND = "MPC Heater Lab"

OVERVIEW_TITLE = "MPC Heater Lab"
OVERVIEW_LEDE = "Compare MPC and PID on the same heater model."
OVERVIEW_MPC_BLURB = (
    "MPC runs a model forward over a horizon, picks a power plan that stays inside "
    "the limits, applies the first move, then re-plans from the measured temperature. "
    "PID only reacts to the error it sees now."
)
OVERVIEW_PAGES = (
    ("Playground", "Set conditions and compare MPC with PID."),
    ("Step-through", "Watch MPC plan one horizon at a time."),
    ("Scorecard", "Compare settling, limit hits, and power use."),
)

PLAYGROUND_TITLE = "Playground"
PLAYGROUND_LEDE = (
    "This page opens on a tight power and rate limit. That is the case where MPC keeps "
    "the slew feasible, and the optimised PID (tuned once on a mild jump, then left alone) "
    "does not."
)
PLAYGROUND_CAPTION = (
    "Dashed lines are the power limits. Optimised PID uses the same gains on every preset: "
    "the ones found on the mild setpoint jump. MPC uses the same planner throughout."
)

STEP_TITLE = "Step-through"
STEP_LEDE = "See how MPC plans each move on the heater."

SCORECARD_TITLE = "Scorecard"
SCORECARD_LEDE = (
    "Same plant, same limits. Optimised PID keeps the gains from the mild setpoint jump. "
    "MPC keeps the same planner. Compare limit hits and settling time."
)
SCORECARD_POWER_TEMPLATE = (
    "Power-limit hits: PID {pid_n}, MPC {mpc_n}, optimised PID {opt_n}. "
    "MPC plans inside the window and the rate limit. The frozen Opt. PID can still clip them."
)
