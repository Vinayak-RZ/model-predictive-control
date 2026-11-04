"""Tests for measured disturbance feedforward and observer tuning."""

from __future__ import annotations

import pytest

from mpc_core.measured_disturbance import (
    MeasuredPlantContext,
    kalman_disturbance_observer_gain,
    steady_state_loss_offset_kw,
)
from mpc_core.twin.ibh import IBHParams


def test_steady_state_loss_offset_ambient_step() -> None:
    nominal = IBHParams(
        m_kg=800.0,
        c_p_j_per_kg_k=480.0,
        eta=0.82,
        U_w_per_k=45.0,
        T_amb_c=25.0,
    )
    measured = MeasuredPlantContext(T_amb_c=33.0, U_w_per_k=45.0)
    du = steady_state_loss_offset_kw(y_c=115.0, nominal=nominal, measured=measured)
    assert du == pytest.approx(-0.43902439024390244)


def test_steady_state_loss_offset_heat_loss_bump() -> None:
    nominal = IBHParams(
        m_kg=800.0,
        c_p_j_per_kg_k=480.0,
        eta=0.82,
        U_w_per_k=45.0,
        T_amb_c=25.0,
    )
    measured = MeasuredPlantContext(T_amb_c=25.0, U_w_per_k=45.0 * 1.45)
    du = steady_state_loss_offset_kw(y_c=115.0, nominal=nominal, measured=measured)
    assert du == pytest.approx(2.222560975609756)


def test_kalman_gain_near_two_for_demo_pole() -> None:
    gain = kalman_disturbance_observer_gain(0.978)
    assert gain == pytest.approx(2.03, rel=0.05)
