"""User-facing UI strings (drafted for write-like-vinayak). Do not polish casually."""

from __future__ import annotations

SIDEBAR_BRAND = "MPC Heater Lab"

OVERVIEW_TITLE = "MPC Heater Lab"
OVERVIEW_LEDE = "Compare MPC and PID on the same heater model."
OVERVIEW_MPC_BLURB = (
    "The optimiser uses a model to plan inputs across a horizon, applies the first move, "
    "then receives the plant’s measured state. This lets MPC plan ahead and respect power "
    "and rate limits, while PID reacts to error."
)
OVERVIEW_PAGES = (
    ("Playground", "Set conditions and compare MPC with PID."),
    ("Step-through", "Watch MPC plan one horizon at a time."),
    ("Scorecard", "Compare settling, limit hits, and power use."),
)

PLAYGROUND_TITLE = "Playground"
PLAYGROUND_LEDE = (
    "Open on tight power limits — that is where MPC’s plan-ahead edge shows against "
    "a strong PID that was optimised once and not retuned."
)
PLAYGROUND_CAPTION = (
    "Dashed lines mark power limits. Optimised PID gains are locked from the mild "
    "setpoint jump (same gains on every preset); MPC is not retuned either."
)

STEP_TITLE = "Step-through"
STEP_LEDE = "See how MPC plans each move on the heater."

SCORECARD_TITLE = "Scorecard"
SCORECARD_LEDE = (
    "Same plant, same limits. Optimised PID uses gains locked from the setpoint jump; "
    "MPC keeps the same planner. Watch limit hits and settling — not a retune contest."
)
SCORECARD_POWER_TEMPLATE = (
    "Power-limit hits: PID {pid_n}, MPC {mpc_n}, optimised PID {opt_n}. "
    "MPC stays inside the window by construction; the frozen Opt. PID can still clip."
)
