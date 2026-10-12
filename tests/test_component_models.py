"""Component models and the non-ideal turbojet (Mattingly, Elements of Propulsion, 2nd ed.,
Ch. 6 and 7). Checks are closed-form limits, conservation laws and textbook identities."""

import numpy as np
import pytest

from propulsion.brayton_cycle import ideal_turbojet
from propulsion.component_models import (
    Components,
    compressor_isentropic_efficiency,
    compressor_pi,
    compressor_tau,
    fuel_air_ratio,
    nozzle_exit,
    ram_recovery,
    turbine_isentropic_efficiency,
    turbine_pi,
    turbine_tau,
    turbojet,
)
from propulsion.flight import FlightCondition
from propulsion.gas import AIR, COMBUSTION_GAS, H_PR_JET_A, entropy_change

CRUISE = FlightCondition.at_altitude(11000.0, 0.8, geopotential=True)
SUPERSONIC = FlightCondition.at_altitude(11000.0, 2.0, geopotential=True)
SLS = FlightCondition.sea_level_static()
MODERN = Components.modern()


def test_ram_recovery_mil_e_5007():
    # MIL-E-5007D schedule: 1 subsonic; 1 - 0.075 (M-1)^1.35 to M 5; 800/(M^4 + 935) above
    assert ram_recovery(0.85) == 1.0
    assert ram_recovery(2.0) == pytest.approx(0.925)
    assert ram_recovery(3.0) == pytest.approx(1 - 0.075 * 2**1.35)
    assert ram_recovery(6.0) == pytest.approx(800 / (6**4 + 935))
    # the two supersonic branches meet (to 4e-4) at M = 5
    assert ram_recovery(5.0) == pytest.approx(ram_recovery(5.0 + 1e-9), abs=4e-4)


@pytest.mark.parametrize("e", [0.85, 0.9, 0.95])
def test_compressor_polytropic_relations(e):
    g = 1.4
    pi = np.array([1.5, 5.0, 20.0, 45.0])
    eta = compressor_isentropic_efficiency(pi, g, e)
    # a multi-stage compressor is less efficient than its stages, more so at high pi
    assert np.all(eta < e) and np.all(np.diff(eta) < 0)
    assert compressor_pi(compressor_tau(pi, g, e), g, e) == pytest.approx(pi)
    assert compressor_isentropic_efficiency(1.0 + 1e-9, g, e) == pytest.approx(e, rel=1e-6)


@pytest.mark.parametrize("e", [0.85, 0.9, 0.95])
def test_turbine_polytropic_relations(e):
    g = 1.3
    tau = np.array([0.9, 0.7, 0.5, 0.3])
    eta = turbine_isentropic_efficiency(tau, g, e)
    # reheat: a multi-stage turbine is *more* efficient than its stages
    assert np.all(eta > e) and np.all(np.diff(eta) > 0)
    assert turbine_tau(turbine_pi(tau, g, e), g, e) == pytest.approx(tau)


def test_polytropic_is_the_limit_of_stage_stacking():
    # stack N identical stages, each of isentropic efficiency e: as N -> inf the overall
    # temperature ratio tends to pi^((g-1)/(g e)) (definition of polytropic efficiency)
    g, e, pi, N = 1.4, 0.88, 30.0, 20000
    r = pi ** (1.0 / N)
    tau_stage = 1.0 + (r ** ((g - 1) / g) - 1.0) / e
    assert tau_stage**N == pytest.approx(compressor_tau(pi, g, e), rel=1e-4)


def test_fuel_air_ratio_energy_balance():
    Tt3, Tt4, eta_b = 700.0, 1600.0, 0.99
    f = fuel_air_ratio(Tt3, Tt4, AIR, COMBUSTION_GAS, H_PR_JET_A, eta_b)
    lhs = (1 + f) * COMBUSTION_GAS.cp * Tt4 - AIR.cp * Tt3
    assert lhs == pytest.approx(eta_b * H_PR_JET_A * f, rel=1e-12)
    f0 = fuel_air_ratio(Tt3, Tt4, AIR, AIR, H_PR_JET_A, include_fuel_mass=False)
    assert f0 == pytest.approx(AIR.cp * (Tt4 - Tt3) / H_PR_JET_A)


def test_nozzle_kinds():
    g = COMBUSTION_GAS.gamma
    critical = ((g + 1) / 2) ** (g / (g - 1))
    P0, Tt = 50e3, 900.0
    # below the critical ratio a convergent nozzle is fully expanded, like the ideal one
    lo = 0.9 * critical * P0
    a = nozzle_exit(lo, Tt, P0, COMBUSTION_GAS, "convergent")
    b = nozzle_exit(lo, Tt, P0, COMBUSTION_GAS, "ideal")
    assert a.P9 == P0 and a.V9 == pytest.approx(b.V9)
    # above it, the convergent nozzle chokes (M9 = 1, P9 > P0) ...
    hi = 4.0 * P0
    c = nozzle_exit(hi, Tt, P0, COMBUSTION_GAS, "convergent")
    d = nozzle_exit(hi, Tt, P0, COMBUSTION_GAS, "ideal")
    assert c.M9 == pytest.approx(1.0) and c.P9 == pytest.approx(hi / critical)
    # ... and full expansion gives the most gross thrust (pressure thrust does not make up for it)
    R = COMBUSTION_GAS.R
    assert c.gross_thrust(1.0, P0, R) < d.gross_thrust(1.0, P0, R)
    assert d.gross_thrust(1.0, P0, R) == pytest.approx(d.V9)
    assert np.isnan(nozzle_exit(0.9 * P0, Tt, P0, COMBUSTION_GAS).V9)


@pytest.mark.parametrize("flight", [SLS, CRUISE, SUPERSONIC])
@pytest.mark.parametrize("pi_c", [3.0, 15.0, 40.0])
def test_ideal_limit_reproduces_phase_1(flight, pi_c):
    real = turbojet(flight, pi_c, 1700.0, Components(), hot=AIR, include_fuel_mass=False)
    ideal = ideal_turbojet(flight, pi_c, 1700.0)
    for name in ("specific_thrust", "tsfc", "f", "eta_thermal", "eta_propulsive", "V9"):
        assert getattr(real, name) == pytest.approx(getattr(ideal, name), rel=1e-12), name
    for k in ideal.stations:
        assert real.stations[k].T == pytest.approx(ideal.stations[k].T, rel=1e-12)
        assert real.stations[k].P == pytest.approx(ideal.stations[k].P, rel=1e-12)


def test_entropy_rises_through_every_lossy_component():
    p = turbojet(SUPERSONIC, 15.0, 1700.0, MODERN)
    st = p.stations
    Pt0, Tt0 = SUPERSONIC.Pt0(), SUPERSONIC.Tt0()

    def ds(gas, a, b):
        return float(entropy_change(gas, a[0], a[1], b[0], b[1]))

    assert ds(AIR, (Tt0, Pt0), (st["2"].T, st["2"].P)) > 0  # inlet shock + friction losses
    assert ds(AIR, (st["2"].T, st["2"].P), (st["3"].T, st["3"].P)) > 0  # compressor
    assert ds(COMBUSTION_GAS, (st["4"].T, st["4"].P), (st["5"].T, st["5"].P)) > 0  # turbine
    Pt9 = st["5"].P * MODERN.pi_n
    Tt9_T9 = (Pt9 / st["9"].P) ** ((COMBUSTION_GAS.gamma - 1) / COMBUSTION_GAS.gamma)
    assert st["5"].T / st["9"].T == pytest.approx(Tt9_T9)  # adiabatic nozzle keeps Tt


def test_power_and_energy_balances():
    p = turbojet(CRUISE, 25.0, 1600.0, MODERN)
    st, f, c = p.stations, p.f, MODERN
    turbine = c.eta_m * (1 + f) * COMBUSTION_GAS.cp * (st["4"].T - st["5"].T)
    assert turbine == pytest.approx(AIR.cp * (st["3"].T - st["2"].T), rel=1e-12)
    ke = 0.5 * ((1 + f) * p.V9**2 - p.V0**2)
    assert p.eta_thermal * f * H_PR_JET_A == pytest.approx(ke, rel=1e-12)
    assert p.eta_overall == pytest.approx(p.V0 * p.specific_thrust / (f * H_PR_JET_A))


def test_losses_cost_thrust_and_fuel():
    # same gas model and fuel-mass treatment, so the difference is the component losses alone
    ideal = turbojet(CRUISE, 20.0, 1600.0, Components())
    real = turbojet(CRUISE, 20.0, 1600.0, MODERN)
    assert real.specific_thrust < ideal.specific_thrust
    assert real.tsfc > ideal.tsfc
    assert real.eta_thermal < ideal.eta_thermal
    assert real.extras["eta_c"] < MODERN.e_c < real.extras["eta_t"]


def test_real_tsfc_has_a_minimum_in_pressure_ratio():
    # with losses, compressor work grows faster than the cycle gains: TSFC is minimum at a
    # finite pi_c, beyond the specific-thrust optimum (Mattingly 2006, Ch. 7 trend)
    pi_c = np.geomspace(2.0, 400.0, 2000)
    p = turbojet(CRUISE, pi_c, 1600.0, MODERN)
    i_s, i_f = np.nanargmin(p.tsfc), np.nanargmax(p.specific_thrust)
    assert 0 < i_s < len(pi_c) - 1
    assert pi_c[i_s] > pi_c[i_f]
    # the ideal cycle has no such minimum: its TSFC falls all the way to the zero-thrust limit
    ideal = ideal_turbojet(CRUISE, pi_c[:1500], 1600.0).tsfc
    assert np.all(np.diff(ideal) < 0)


def test_convergent_nozzle_under_expands():
    p = turbojet(CRUISE, 20.0, 1600.0, MODERN, nozzle="convergent")
    q = turbojet(CRUISE, 20.0, 1600.0, MODERN)
    assert p.extras["M9"] == pytest.approx(1.0) and p.extras["P9"] > CRUISE.P0
    assert p.specific_thrust < q.specific_thrust


def test_tsfc_undefined_without_thrust():
    # past the zero-thrust pressure ratio the engine makes drag: TSFC must not go negative
    pi_c = np.geomspace(2.0, 400.0, 500)
    p = turbojet(CRUISE, pi_c, 1400.0, MODERN)
    assert np.any(p.specific_thrust < 0)
    assert np.all(np.isnan(p.tsfc[p.specific_thrust <= 0]))
    assert np.all(p.tsfc[p.specific_thrust > 0] > 0)
