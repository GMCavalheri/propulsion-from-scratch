"""Two-spool separate-exhaust turbofan. Ideal-limit checks use the closed forms of the ideal
turbofan (Mattingly, Elements of Propulsion, 2nd ed., Ch. 5); the non-ideal model is
checked through its limits and conservation laws."""

import numpy as np
import pytest

from propulsion.component_models import Components, turbojet
from propulsion.flight import FlightCondition
from propulsion.gas import AIR, COMBUSTION_GAS, H_PR_JET_A
from propulsion.turbofan_model import (
    ideal_jet_velocities,
    optimum_bypass_ratio,
    optimum_fan_pressure_ratio,
    turbofan,
)

CRUISE = FlightCondition.at_altitude(10668.0, 0.78, geopotential=True)
SLS = FlightCondition.sea_level_static()
MODERN = Components.modern()
IDEAL = {"components": Components(), "hot": AIR, "include_fuel_mass": False}


@pytest.mark.parametrize("flight", [SLS, CRUISE])
def test_zero_bypass_is_a_turbojet(flight):
    # with alpha = 0 the fan, booster and HPC are just one compressor of ratio pi_c
    for kw in (IDEAL, {"components": MODERN.with_(e_f=MODERN.e_c)}):
        fan = turbofan(flight, 0.0, 1.6, 25.0, 1600.0, pi_cL=1.8, **kw)
        jet = turbojet(flight, 25.0, 1600.0, **kw)
        for name in ("specific_thrust", "tsfc", "f", "eta_thermal", "eta_propulsive", "V9"):
            assert getattr(fan, name) == pytest.approx(getattr(jet, name), rel=1e-12), name
        assert fan.extras["specific_thrust_fan"] == 0.0


@pytest.mark.parametrize("alpha", [0.5, 5.0, 10.0])
def test_ideal_limit_matches_closed_form(alpha):
    p = turbofan(CRUISE, alpha, 1.6, 30.0, 1600.0, pi_cL=1.5, **IDEAL)
    V9, V19 = ideal_jet_velocities(CRUISE, alpha, 1.6, 30.0, 1600.0)
    assert p.V9 == pytest.approx(V9, rel=1e-12)
    assert p.extras["V19"] == pytest.approx(V19, rel=1e-12)
    expected = ((V9 - p.V0) + alpha * (V19 - p.V0)) / (1 + alpha)
    assert p.specific_thrust == pytest.approx(expected, rel=1e-12)
    # f per unit core air and the ideal thermal efficiency 1 - 1/(tau_r tau_c)
    tau_r, tau_c = CRUISE.tau_r(), 30.0 ** (0.4 / 1.4)
    assert p.f == pytest.approx(
        AIR.cp * CRUISE.T0 * (1600 / CRUISE.T0 - tau_r * tau_c) / H_PR_JET_A
    )
    assert p.eta_thermal == pytest.approx(1 - 1 / (tau_r * tau_c), rel=1e-12)


def test_booster_split_does_not_matter_when_ideal():
    # an ideal cycle only sees the overall pressure ratio, not how it is split between spools
    a = turbofan(CRUISE, 6.0, 1.6, 30.0, 1600.0, pi_cL=1.0, **IDEAL)
    b = turbofan(CRUISE, 6.0, 1.6, 30.0, 1600.0, pi_cL=2.5, **IDEAL)
    assert a.specific_thrust == pytest.approx(b.specific_thrust, rel=1e-12)


def test_optimum_bypass_ratio():
    pi_f, pi_c, Tt4 = 1.7, 30.0, 1600.0
    alpha = np.linspace(0.0, 20.0, 200001)
    p = turbofan(CRUISE, alpha, pi_f, pi_c, Tt4, **IDEAL)
    best = alpha[np.nanargmin(p.tsfc)]
    a_star = optimum_bypass_ratio(CRUISE, pi_f, pi_c, Tt4)
    assert best == pytest.approx(a_star, abs=2e-4)
    # at the optimum the core jet's excess velocity is half the fan jet's
    q = turbofan(CRUISE, a_star, pi_f, pi_c, Tt4, **IDEAL)
    assert q.V9 - q.V0 == pytest.approx(0.5 * (q.extras["V19"] - q.V0), rel=1e-9)


def test_optimum_fan_pressure_ratio():
    alpha, pi_c, Tt4 = 8.0, 35.0, 1600.0
    pi_f = np.linspace(1.05, 3.0, 200001)
    p = turbofan(CRUISE, alpha, pi_f, pi_c, Tt4, **IDEAL)
    best = pi_f[np.nanargmin(p.tsfc)]
    pf_star = optimum_fan_pressure_ratio(CRUISE, alpha, pi_c, Tt4)
    assert best == pytest.approx(pf_star, abs=2e-5)
    # at the optimum both jets leave equally fast
    q = turbofan(CRUISE, alpha, pf_star, pi_c, Tt4, **IDEAL)
    assert q.V9 == pytest.approx(q.extras["V19"], rel=1e-9)


@pytest.mark.parametrize("flight", [SLS, CRUISE])
def test_spool_power_balances_and_thrust_split(flight):
    p = turbofan(flight, 5.5, 1.65, 32.0, 1550.0, pi_cL=1.6, components=MODERN)
    st, f, m = p.stations, p.f, MODERN.eta_m
    cpc, cpt = AIR.cp, COMBUSTION_GAS.cp
    hp = m * (1 + f) * cpt * (st["4"].T - st["45"].T)
    assert hp == pytest.approx(cpc * (st["3"].T - st["25"].T), rel=1e-12)
    lp = m * (1 + f) * cpt * (st["45"].T - st["5"].T)
    fan_and_booster = cpc * (6.5 * (st["13"].T - st["2"].T) + (st["25"].T - st["13"].T))
    assert lp == pytest.approx(fan_and_booster, rel=1e-12)
    e = p.extras
    assert e["specific_thrust_core"] + e["specific_thrust_fan"] == pytest.approx(
        p.specific_thrust, rel=1e-12
    )
    # thermal efficiency is the kinetic-energy gain of both streams over the fuel energy
    ke = 0.5 * ((1 + f) * p.V9**2 + 5.5 * e["V19"] ** 2 - 6.5 * p.V0**2)
    assert p.eta_thermal * f * H_PR_JET_A == pytest.approx(ke, rel=1e-12)
    assert st["3"].P / st["2"].P == pytest.approx(32.0)


def test_bypass_raises_propulsive_efficiency():
    # the reason turbofans exist: at fixed core, more bypass -> slower jets -> higher eta_p
    alpha = np.array([0.0, 2.0, 5.0, 9.0])
    p = turbofan(CRUISE, alpha, 1.5, 35.0, 1600.0, components=MODERN)
    assert np.all(np.diff(p.eta_propulsive) > 0)
    assert np.all(np.diff(p.tsfc) < 0)
    assert np.all(np.diff(p.specific_thrust) < 0)


def test_convergent_nozzles():
    p = turbofan(
        CRUISE,
        5.5,
        1.65,
        32.0,
        1550.0,
        components=MODERN,
        core_nozzle="convergent",
        fan_nozzle="convergent",
    )
    q = turbofan(CRUISE, 5.5, 1.65, 32.0, 1550.0, components=MODERN)
    # fan nozzle pressure ratio at cruise is above critical (~1.89): the fan jet chokes
    assert p.extras["M19"] == pytest.approx(1.0)
    assert p.specific_thrust < q.specific_thrust
    # but the loss is small for a turbofan (low nozzle pressure ratios)
    assert p.specific_thrust > 0.97 * q.specific_thrust


def test_efficiencies_with_under_expanded_nozzles():
    # Lesson 3: full expansion maximises thrust, so measuring jet power with fully expanded
    # velocities keeps eta_p below 2/(1 + V_full/V0) < 1, and eta_o = eta_t eta_p still holds.
    p = turbofan(
        CRUISE,
        5.5,
        1.8,
        30.0,
        1300.0,
        pi_cL=1.6,
        components=MODERN,
        core_nozzle="convergent",
        fan_nozzle="convergent",
    )
    assert p.extras["M19"] == pytest.approx(1.0) and p.extras["M9"] == pytest.approx(1.0)
    assert 0 < p.eta_propulsive < 1
    assert p.eta_overall == pytest.approx(p.V0 * 6.5 * p.specific_thrust / (p.f * H_PR_JET_A))
    q = turbofan(CRUISE, 5.5, 1.8, 30.0, 1300.0, pi_cL=1.6, components=MODERN)
    assert p.eta_thermal == pytest.approx(q.eta_thermal, rel=1e-12)  # same jet energy
    assert p.eta_propulsive < q.eta_propulsive  # under-expansion wastes some of it
