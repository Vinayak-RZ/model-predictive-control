"""CasADi IBH twin step tests. Fixture values are test-only, not plant defaults."""

from __future__ import annotations

from pathlib import Path

import pytest

from mpc_from_stamped.twin.codegen import generate_ibh_step_c, write_ibh_step_c
from mpc_from_stamped.twin.ibh import (
    IBH_PARAM_NAMES,
    OpenTwinParameter,
    ibh_step_function,
    require_params,
    step_ibh,
)

# Fixture values for tests only. Not plant defaults and not product thresholds.
FIXTURE = {
    "m_kg": 2.0,
    "c_p_j_per_kg_k": 500.0,
    "eta": 0.5,
    "U_w_per_k": 10.0,
    "T_amb_c": 25.0,
}


def test_require_params_lists_every_open_name() -> None:
    with pytest.raises(OpenTwinParameter) as ei:
        require_params({})
    assert ei.value.names == list(IBH_PARAM_NAMES)


def test_require_params_partial_open() -> None:
    partial = dict(FIXTURE)
    del partial["eta"]
    with pytest.raises(OpenTwinParameter) as ei:
        require_params(partial)
    assert ei.value.names == ["eta"]


def test_casadi_step_matches_heat_balance_formula() -> None:
    params = require_params(FIXTURE)
    # T=25, P=1000, dt=1 → dT = 0.5; T_next = 25.5
    got = step_ibh(T_c=25.0, P_coil_w=1000.0, dt_s=1.0, params=params)
    assert got == pytest.approx(25.5)


def test_casadi_function_signature() -> None:
    fn = ibh_step_function()
    assert fn.name() == "ibh_step"
    assert fn.n_in() == 4
    assert fn.n_out() == 1


def test_rejects_non_positive_dt() -> None:
    params = require_params(FIXTURE)
    with pytest.raises(ValueError, match="dt_s"):
        step_ibh(T_c=25.0, P_coil_w=1000.0, dt_s=0.0, params=params)


def test_write_ibh_step_c_round_trip(tmp_path: Path) -> None:
    write_ibh_step_c(tmp_path / "generated")
    assert (tmp_path / "generated" / "ibh_step.c").read_text() == generate_ibh_step_c()
    assert (tmp_path / "include" / "stamped" / "ibh_step.h").is_file()
    # No invented plant constants in the C body (only formula + p[] reads).
    checked = generate_ibh_step_c()
    assert "480" not in checked
    assert "140" not in checked
