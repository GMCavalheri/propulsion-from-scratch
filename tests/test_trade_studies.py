"""Trade-study tools: the fan optimiser against the ideal closed form, geometric identities of
the size proxy, the scaling of the jet-noise proxy, and the classical design trends
(Mattingly, Elements of Propulsion, 2nd ed., Ch. 5 and 7)."""

import numpy as np
import pytest

from propulsion.brayton_cycle import ideal_turbojet
from propulsion.component_models import Components
from propulsion.flight import FlightCondition
from propulsion.gas import AIR, mass_flow_parameter
from propulsion.trade_studies import best_fan_pressure_ratio, fan_diameter, jet_noise_index, sweep
from propulsion.turbofan_model import optimum_fan_pressure_ratio, turbofan
from propulsion.units import FT

FL350 = FlightCondition.at_altitude(35000 * FT, 0.78, geopotential=True)
SLS = FlightCondition.sea_level_static()
IDEAL = {"components": Components(), "hot": AIR, "include_fuel_mass": False}


@pytest.mark.parametrize("alpha", [3.0, 8.0, 12.0])
def test_best_fan_matches_ideal_closed_form(alpha):
    # at alpha = 3 the optimum (5.6) is above the default search cap of 4, so raise it
    pf = best_fan_pressure_ratio(FL350, alpha, 35.0, 1600.0, pi_f_max=10.0, **IDEAL)
    assert pf == pytest.approx(optimum_fan_pressure_ratio(FL350, alpha, 35.0, 1600.0), rel=1e-6)


def test_sweep_agrees_with_direct_evaluation():
    s = sweep(FL350, [4.0, 9.0], [30.0, 45.0], 1500.0, pi_cL=1.6)
    assert s.tsfc.shape == (2, 2, 1)
    p = turbofan(
        FL350, 9.0, s.pi_f[1, 0, 0], 30.0, 1500.0, pi_cL=1.6, components=Components.modern()
    )
    assert s.tsfc[1, 0, 0] == pytest.approx(float(p.tsfc), rel=1e-12)
    assert s.Tt3[1, 1, 0] > s.Tt3[1, 0, 0]  # higher OPR, hotter compressor exit


def test_fan_diameter_inverts_the_mass_flow_parameter():
    D = fan_diameter(350.0, SLS, M2=0.6, hub_tip=0.3)
    area = np.pi / 4 * D**2 * (1 - 0.3**2)
    mdot = mass_flow_parameter(0.6, AIR) * 101325.0 * area / np.sqrt(288.15)
    assert mdot == pytest.approx(350.0, rel=1e-12)
    # diameter scales as sqrt(flow)
    assert fan_diameter(4 * 350.0, SLS) == pytest.approx(2 * D)


def test_jet_noise_index_scaling():
    # one stream at fixed thrust, static: F = mdot V, so the jet carries (1 + f) mdot V^7
    # = (1 + f) F V^6 -> 60 log10(V ratio) dB plus the small fuel-mass term
    a = ideal_turbojet(SLS, 10.0, 1400.0)
    b = ideal_turbojet(SLS, 10.0, 1800.0)
    expected = 60.0 * np.log10(float(b.V9) / float(a.V9)) + 10.0 * np.log10(
        (1 + float(b.f)) / (1 + float(a.f))
    )
    assert jet_noise_index(b, 1e5) - jet_noise_index(a, 1e5) == pytest.approx(expected, rel=1e-9)


def test_classical_trends():
    alpha = np.array([2.0, 4.0, 6.0, 8.0, 10.0, 12.0])
    s = sweep(FL350, alpha, [25.0, 40.0], 1500.0, pi_cL=1.6)
    tsfc = s.tsfc[:, :, 0]
    # TSFC falls with bypass ratio and with overall pressure ratio ...
    assert np.all(np.diff(tsfc, axis=0) < 0)
    assert np.all(tsfc[:, 1] < tsfc[:, 0])
    # ... while specific thrust and the best fan pressure ratio fall with bypass ratio
    assert np.all(np.diff(s.specific_thrust[:, 0, 0]) < 0)
    assert np.all(np.diff(s.pi_f[:, 0, 0]) < 0)
    # bigger fans and quieter jets for the same thrust
    sls = sweep(SLS, alpha, 30.0, 1500.0, pi_cL=1.6)
    mdot = 120e3 / sls.specific_thrust[:, 0, 0]
    assert np.all(np.diff(fan_diameter(mdot, SLS)) > 0)
    noise = [
        jet_noise_index(
            turbofan(SLS, a, pf, 30.0, 1500.0, pi_cL=1.6, components=Components.modern()), 120e3
        )
        for a, pf in zip(alpha, sls.pi_f[:, 0, 0], strict=True)
    ]
    assert np.all(np.diff(noise) < 0)
