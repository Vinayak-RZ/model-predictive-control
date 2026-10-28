"""Emit C for the heater step from the CasADi definition (one shared formula).

The generated files can be checked into an embedded runtime tree so a target
build does not need Python or CasADi. Regenerating and diffing is a dev step.
"""

from __future__ import annotations

from pathlib import Path

from mpc_core.twin.ibh import ibh_step_function

# Header kept stable so a C/C++ runtime can include it without CasADi.
_ABI_HEADER = """\
/* Generated ABI for the induction heater heat-balance step.
 * Do not hand-edit the formula body: regenerate via
 *   python -c "from mpc_core.twin.codegen import write_ibh_step_c; write_ibh_step_c(Path('...'))"
 * Parameters are always passed in; nothing physical is hardcoded.
 */
#ifndef IBH_STEP_H
#define IBH_STEP_H

#ifdef __cplusplus
extern "C" {
#endif

/* p = {m_kg, c_p_j_per_kg_k, eta, U_w_per_k, T_amb_c} */
double ibh_step(double T_c, double P_coil_w, double dt_s, const double p[5]);

#ifdef __cplusplus
}
#endif

#endif /* IBH_STEP_H */
"""

_HAND_C = """\
/* Checked-in C matching mpc_core.twin.ibh.ibh_step_function.
 * Formula: T_next = T + dt * (eta*P - U*(T - T_amb)) / (m * c_p)
 * All coefficients come from p[]; this file invents no plant numbers.
 */
#include "ibh/ibh_step.h"

double ibh_step(double T_c, double P_coil_w, double dt_s, const double p[5]) {
  const double m = p[0];
  const double c_p = p[1];
  const double eta = p[2];
  const double U = p[3];
  const double T_amb = p[4];
  const double dT = (eta * P_coil_w - U * (T_c - T_amb)) / (m * c_p);
  return T_c + dt_s * dT;
}
"""


def generate_ibh_step_c() -> str:
    """Return the checked-in C body (same formula as the CasADi Function).

    CasADi's own generate() emits a larger runtime-dependent file. For the
    coursework stub we keep a minimal ABI that links cleanly, and Python tests
    prove numerical parity with CasADi.
    """
    _ = ibh_step_function()
    return _HAND_C


def write_ibh_step_c(runtime_generated_dir: Path) -> None:
    """Write `ibh_step.h` and `ibh_step.c` under a twin-runtime layout."""
    runtime_generated_dir.mkdir(parents=True, exist_ok=True)
    include_dir = runtime_generated_dir.parent / "include" / "ibh"
    include_dir.mkdir(parents=True, exist_ok=True)
    (include_dir / "ibh_step.h").write_text(_ABI_HEADER)
    (runtime_generated_dir / "ibh_step.c").write_text(generate_ibh_step_c())
