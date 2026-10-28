#!/usr/bin/env python3
"""Illustrative closed-loop demo: identified-linear plant + offset-free MPC.

Numbers below are the same illustrative ARX used in the unit tests
(a=0.9, b=0.05, not plant data). Nothing here writes to a plant.
"""

from __future__ import annotations

from mpc_from_stamped import (
    IdentifiedLinearModel,
    MpcState,
    SetpointLimits,
    solve,
)
from mpc_from_stamped.twin.ibh import require_params, step_ibh


def main() -> None:
    model = IdentifiedLinearModel(
        fit_id="fit-demo-illustrative",
        a=0.9,
        b=0.05,
        dt_s=1.0,
        n_samples=200,
        residual_rms=1e-9,
        experiment="step",
    )
    limits = SetpointLimits("power_setpoint", "kW", 900.0, 1100.0, 50.0)
    y = 500.0
    u = 1000.0
    y_ref = 510.0
    state = MpcState()
    print("offset-free MPC on identified linear model (illustrative)")
    print(f"y_ref={y_ref}, horizon_steps=20, time_limit_s=2.0")
    for k in range(8):
        result = solve(
            model,
            [limits],
            {"power_setpoint": u},
            y_meas=y,
            y_ref=y_ref,
            horizon_steps=20,
            time_limit_s=2.0,
            state=state,
        )
        u_next = result.best["power_setpoint"]
        # True plant for the demo: same ARX as the controller model (perfect match).
        y = model.a * y + model.b * u_next + 0.0
        state = result.state
        print(
            f"k={k:02d} u={u_next:8.3f} y={y:8.3f} "
            f"d_hat={result.d_hat:8.4f} active={result.active_constraints}"
        )
        u = u_next

    print()
    print("CasADi IBH twin one-step (illustrative fixture params, not plant data)")
    params = require_params(
        {
            "m_kg": 2.0,
            "c_p_j_per_kg_k": 500.0,
            "eta": 0.5,
            "U_w_per_k": 10.0,
            "T_amb_c": 25.0,
        }
    )
    t_next = step_ibh(T_c=25.0, P_coil_w=1000.0, dt_s=1.0, params=params)
    print(f"T_c=25, P_coil_w=1000, dt_s=1 → T_next={t_next}")


if __name__ == "__main__":
    main()
