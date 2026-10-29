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
    ("Scorecard", "Compare tracking, limits, and power use."),
)

PLAYGROUND_TITLE = "Playground"
PLAYGROUND_LEDE = "Set the conditions and compare MPC with PID on the heater."
PLAYGROUND_CAPTION = (
    "Dashed lines mark power limits; traces show each controller response."
)

STEP_TITLE = "Step-through"
STEP_LEDE = "See how MPC plans each move on the heater."

SCORECARD_TITLE = "Scorecard"
SCORECARD_LEDE = (
    "Compare MPC, hand-tuned PID, and optimised PID against the same targets."
)
SCORECARD_POWER_TEMPLATE = (
    "Power-limit violations: PID {pid_n}, MPC {mpc_n}, optimised PID {opt_n}."
)
