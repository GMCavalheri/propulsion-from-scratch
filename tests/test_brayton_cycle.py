"""Ideal Brayton cycle and ideal turbojet. Every check is a closed-form identity of the ideal
cycle (Mattingly, Elements of Propulsion, 2nd ed., Ch. 2 and 5)."""

import numpy as np
import pytest

from propulsion.brayton_cycle import (
    brayton_optimum_tau,
    brayton_specific_work,
    brayton_thermal_efficiency,
    ideal_turbojet,
    optimum_compressor_pressure_ratio,
    ts_diagram,
)
from propulsion.flight import FlightCondition
from propulsion.gas import AIR, H_PR_JET_A

CRUISE = FlightCondition.at_altitude(11000.0, 0.85, geopotential=True)
SUPERSONIC = FlightCondition(M0=2.0, T0=216.65, P0=19.4e3)
SLS = FlightCondition.sea_level_static()


def test_closed_brayton_efficiency():
    # eta = 1 - 1/tau, independent of tau_lambda
    assert brayton_thermal_efficiency(20.0) == pytest.approx(1 - 20.0 ** (-0.4 / 1.4))


def test_closed_brayton_work_optimum():
    tau_lambda = 6.0
    pi = np.linspace(1.01, 200.0, 200001)
    w = brayton_specific_work(pi, tau_lambda)
    tau_best = pi[np.argmax(w)] ** (0.4 / 1.4)
    assert tau_best == pytest.approx(brayton_optimum_tau(tau_lambda), rel=1e-4)
    # zero net work when tau = 1 or tau = tau_lambda
    assert brayton_specific_work(tau_lambda**3.5, tau_lambda) == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("flight", [SLS, CRUISE, SUPERSONIC])
@pytest.mark.parametrize("pi_c", [4.0, 12.0, 30.0])
def test_energy_balances_close(flight, pi_c):
    p = ideal_turbojet(flight, pi_c, 1600.0)
    st = p.stations
    # turbine work = compressor work
    assert st["4"].T - st["5"].T == pytest.approx(st["3"].T - st["2"].T, rel=1e-12)
    # thermal efficiency = kinetic-energy gain / fuel energy, and = 1 - 1/(tau_r tau_c)
    ke = 0.5 * (p.V9**2 - p.V0**2)
    assert ke / (p.f * H_PR_JET_A) == pytest.approx(p.eta_thermal, rel=1e-12)
    # overall = thrust power / fuel power = eta_th * eta_p
    if flight.M0 > 0:
        eta_o = p.V0 * p.specific_thrust / (p.f * H_PR_JET_A)
        assert eta_o == pytest.approx(p.eta_overall, rel=1e-12)
    # burner: fuel energy = cp (Tt4 - Tt3)
    assert p.f * H_PR_JET_A == pytest.approx(AIR.cp * (st["4"].T - st["3"].T), rel=1e-12)


def test_static_thermal_efficiency_equals_closed_cycle():
    # at M0 = 0 the turbojet is the closed Brayton cycle with the atmosphere as the cold sink
    p = ideal_turbojet(SLS, 25.0, 1700.0)
    assert p.eta_thermal == pytest.approx(brayton_thermal_efficiency(25.0))
    assert p.eta_propulsive == 0.0 and p.specific_thrust > 0


def test_isentropic_and_heat_addition():
    p = ideal_turbojet(CRUISE, 20.0, 1600.0)
    st = p.stations
    s = {k: float(v.entropy(st["0"])) for k, v in st.items()}
    assert s["2"] == pytest.approx(0.0, abs=1e-9)
    assert s["3"] == pytest.approx(0.0, abs=1e-9)
    assert s["5"] == pytest.approx(s["4"], abs=1e-9)
    assert s["9"] == pytest.approx(s["4"], abs=1e-9)
    assert s["4"] > 100.0  # heat addition raises entropy
    # nozzle exit is at ambient pressure and T9 = Tt4 / (tau_r tau_c)
    assert st["9"].T == pytest.approx(1600.0 / (p.extras["tau_r"] * p.extras["tau_c"]))


@pytest.mark.parametrize("flight", [SLS, CRUISE, SUPERSONIC])
def test_optimum_pressure_ratio(flight):
    Tt4 = 1700.0
    pi_c = np.geomspace(1.0, 80.0, 400001)
    p = ideal_turbojet(flight, pi_c, Tt4)
    best = pi_c[np.nanargmax(p.specific_thrust)]
    opt = optimum_compressor_pressure_ratio(flight, Tt4)
    assert best == pytest.approx(opt, rel=2e-3)
    p_opt = ideal_turbojet(flight, opt, Tt4)
    assert p_opt.stations["9"].T == pytest.approx(p_opt.stations["3"].T, rel=1e-12)


def test_thrust_vanishes_at_maximum_compression():
    # when tau_r tau_c -> tau_lambda no heat can be added: f -> 0 and V9 -> V0
    Tt4 = 1500.0
    pi_max = (Tt4 / CRUISE.Tt0()) ** 3.5
    p = ideal_turbojet(CRUISE, pi_max * (1 - 1e-9), Tt4)
    assert p.f == pytest.approx(0.0, abs=1e-9)
    assert p.specific_thrust == pytest.approx(0.0, abs=1e-3)
    assert np.isnan(ideal_turbojet(CRUISE, pi_max * 1.1, Tt4).specific_thrust)


def test_ramjet_limit():
    # pi_c = 1 is the ideal ramjet: eta_th = 1 - 1/tau_r, no static thrust
    p = ideal_turbojet(SUPERSONIC, 1.0, 1800.0)
    assert p.eta_thermal == pytest.approx(1 - 1 / SUPERSONIC.tau_r())
    assert p.specific_thrust > 0
    assert ideal_turbojet(SLS, 1.0, 1800.0).specific_thrust == pytest.approx(0.0)


def test_broadcasting():
    p = ideal_turbojet(CRUISE, np.array([[5.0], [10.0], [20.0]]), np.array([1400.0, 1600.0]))
    assert p.specific_thrust.shape == (3, 2)
    # more Tt4 -> more specific thrust; TSFC rises with Tt4 for the ideal turbojet
    assert np.all(np.diff(p.specific_thrust, axis=1) > 0)


def test_ts_diagram_closes():
    labels, T, s, Tp, sp = ts_diagram(ideal_turbojet(CRUISE, 20.0, 1600.0))
    assert labels == ["0", "2", "3", "4", "5", "9"]
    assert Tp[0] == pytest.approx(T[0]) and Tp[-1] == pytest.approx(T[0])
    assert sp[-1] == pytest.approx(0.0, abs=1e-9)
