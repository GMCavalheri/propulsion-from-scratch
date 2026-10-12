"""Off-design performance of a fixed-geometry turbofan (Mattingly, Elements of Propulsion,
2nd ed., Ch. 8 method). Checks: exact reproduction of the design point, the matching
constraints, dimensional similarity (corrected parameters) and the textbook trends."""

import numpy as np
import pytest

from propulsion.flight import FlightCondition
from propulsion.gas import mass_flow_parameter
from propulsion.off_design_performance import TurbofanEngine
from propulsion.units import FT

SLS = FlightCondition.sea_level_static()
FL350 = FlightCondition.at_altitude(35000 * FT, 0.78, geopotential=True)
DESIGN = {"alpha": 5.1, "pi_f": 1.65, "pi_c": 32.8, "Tt4": 1650.0, "pi_cL": 1.6}


@pytest.fixture(scope="module")
def engine():
    return TurbofanEngine.design(SLS, thrust=117e3, **DESIGN)


def test_design_point_is_reproduced(engine):
    d = engine.design_point
    p = engine.operate(SLS, DESIGN["Tt4"])
    assert p.converged
    for name in ("alpha", "pi_f", "pi_cL", "pi_cH", "mdot_core", "thrust", "fuel_flow"):
        assert getattr(p, name) == pytest.approx(getattr(d, name), rel=1e-9), name
    assert p.N1 == pytest.approx(1.0) and p.N2 == pytest.approx(1.0)
    assert d.thrust == pytest.approx(117e3)


def test_sizing_by_flow_or_thrust_agree(engine):
    d = engine.design_point
    other = TurbofanEngine.design(SLS, mdot0=d.mdot0, **DESIGN)
    assert other.design_point.thrust == pytest.approx(d.thrust, rel=1e-12)
    with pytest.raises(ValueError):
        TurbofanEngine.design(SLS, **DESIGN)


@pytest.mark.parametrize("flight, Tt4", [(SLS, 1200.0), (FL350, 1450.0), (FL350, 1100.0)])
def test_matching_constraints_hold(engine, flight, Tt4):
    p = engine.operate(flight, Tt4)
    assert p.converged
    st, ex = p.cycle.stations, p.cycle.extras
    # choked HPT nozzle: mdot4 sqrt(Tt4) / Pt4 unchanged; HPT temperature ratio unchanged
    m4 = p.mdot_core * (1 + float(p.cycle.f))
    assert m4 * np.sqrt(Tt4) / float(st["4"].P) == pytest.approx(engine.C4, rel=1e-8)
    assert float(ex["tau_tH"]) == pytest.approx(engine.tau_tH, rel=1e-8)
    # implied, not imposed: the LPT nozzle (station 45) passes the same corrected flow too
    d = engine.design_point
    c45 = m4 * np.sqrt(float(st["45"].T)) / float(st["45"].P)
    m4d = d.mdot_core * (1 + float(d.cycle.f))
    c45d = m4d * np.sqrt(float(d.cycle.stations["45"].T)) / float(d.cycle.stations["45"].P)
    assert c45 == pytest.approx(c45d, rel=1e-8)
    # bypass flow fits the fixed fan-nozzle area
    Pt19 = float(st["13"].P) * engine.components.pi_fn
    A19 = (
        p.alpha
        * p.mdot_core
        * np.sqrt(float(st["13"].T))
        / (Pt19 * mass_flow_parameter(float(ex["M19"]), engine.cold))
    )
    assert A19 == pytest.approx(engine.A19, rel=1e-8)


def test_continuation_is_path_independent(engine):
    direct = engine.operate(FL350, 1150.0)
    via = engine.operate(FL350, 1150.0, guess=engine.operate(FL350, 1500.0))
    assert direct.converged and via.converged
    assert direct.thrust == pytest.approx(via.thrust, rel=1e-9)
    assert direct.alpha == pytest.approx(via.alpha, rel=1e-9)


def test_corrected_parameters_are_similar():
    # Dimensional analysis: with the fuel mass neglected, an engine at the same M0 and the
    # same Tt4/T0 runs at the same corrected condition at any altitude. Then pressure ratios,
    # bypass ratio and corrected speed are identical; thrust scales with delta0 and flow with
    # delta0 / sqrt(theta0) (Mattingly 2006, Ch. 8; Walsh & Fletcher, Gas Turbine Performance).
    e = TurbofanEngine.design(SLS, thrust=117e3, include_fuel_mass=False, **DESIGN)
    a = FlightCondition.at_altitude(3000.0, 0.5)
    b = FlightCondition.at_altitude(9000.0, 0.5)
    pa = e.operate(a, 1300.0)
    pb = e.operate(b, 1300.0 * b.T0 / a.T0)
    for name in ("alpha", "pi_f", "pi_cL", "pi_cH", "N1_corrected", "corrected_flow"):
        assert getattr(pa, name) == pytest.approx(getattr(pb, name), rel=1e-8), name
    assert pa.thrust / a.P0 == pytest.approx(pb.thrust / b.P0, rel=1e-8)


def test_throttle_trends_at_takeoff(engine):
    Tt4 = np.linspace(1650.0, 800.0, 18)
    pts, guess = [], None
    for t in Tt4:
        guess = engine.operate(SLS, t, guess=guess)
        pts.append(guess)
    assert all(p.converged for p in pts)
    thrust = np.array([p.thrust for p in pts])
    tsfc = np.array([p.tsfc for p in pts])
    # throttling back lowers thrust and both spool speeds, and raises the bypass ratio
    assert np.all(np.diff(thrust) < 0)
    assert np.all(np.diff([p.N1 for p in pts]) < 0)
    assert np.all(np.diff([p.N2 for p in pts]) < 0)
    assert pts[-3].alpha > pts[0].alpha
    # the LP spool slows more than the HP spool
    assert pts[-1].N1 < pts[-1].N2
    # TSFC has a part-power minimum and rises again towards idle
    i = int(np.argmin(tsfc))
    assert 0 < i < len(tsfc) - 1


def test_lapse_with_altitude_and_speed(engine):
    sls = engine.operate(SLS, 1500.0)
    climb = engine.operate(FlightCondition.at_altitude(5000.0, 0.5), 1500.0)
    cruise = engine.operate(FL350, 1500.0)
    assert sls.thrust > climb.thrust > cruise.thrust
    assert cruise.tsfc > climb.tsfc > sls.tsfc  # TSFC rises with flight speed
    # thrust lapse at cruise is roughly the pressure ratio delta0 (here within a factor 1.5)
    lapse = cruise.thrust / sls.thrust
    assert 0.6 * FL350.P0 / SLS.P0 < lapse < 1.5 * FL350.P0 / SLS.P0
    # at fixed Tt4 the colder air at altitude means a higher corrected speed
    assert cruise.N1_corrected > sls.N1_corrected


def test_operate_at_thrust(engine):
    target = 0.3 * engine.design_point.thrust
    p = engine.operate_at_thrust(SLS, target)
    assert p.converged
    assert p.thrust == pytest.approx(target, rel=1e-6)
    assert p.Tt4 < engine.design_point.Tt4
