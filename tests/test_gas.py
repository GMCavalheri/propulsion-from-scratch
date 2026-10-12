import numpy as np
import pytest

from propulsion.gas import (
    AIR,
    COMBUSTION_GAS,
    area_ratio,
    entropy_change,
    mach_from_area_ratio,
    mach_from_pressure_ratio,
    mass_flow_parameter,
    stagnation_pressure_ratio,
    stagnation_temperature_ratio,
)


def test_gas_constants():
    # R = cp (g-1)/g: 1004 * 0.4 / 1.4 = 286.857; 1239 * 0.3 / 1.3 = 285.923
    assert AIR.R == pytest.approx(286.857, abs=1e-3)
    assert COMBUSTION_GAS.R == pytest.approx(285.923, abs=1e-3)


def test_isentropic_table_values():
    # Anderson, Modern Compressible Flow, App. A (gamma = 1.4), M = 2: Pt/P = 7.824, Tt/T = 1.8,
    # A/A* = 1.688; M = 0.5: Pt/P = 1.186, A/A* = 1.340
    assert stagnation_temperature_ratio(2.0, 1.4) == pytest.approx(1.8)
    assert stagnation_pressure_ratio(2.0, 1.4) == pytest.approx(7.824, abs=1e-3)
    assert area_ratio(2.0, 1.4) == pytest.approx(1.688, abs=1e-3)
    assert stagnation_pressure_ratio(0.5, 1.4) == pytest.approx(1.186, abs=1e-3)
    assert area_ratio(0.5, 1.4) == pytest.approx(1.340, abs=1e-3)


def test_critical_pressure_ratio():
    # choking pressure ratio Pt/P* = ((g+1)/2)^(g/(g-1)) = 1.8929 for g = 1.4
    assert stagnation_pressure_ratio(1.0, 1.4) == pytest.approx(1.2**3.5)
    assert area_ratio(1.0, 1.4) == pytest.approx(1.0)


@pytest.mark.parametrize("M", [0.1, 0.5, 0.85, 1.0, 1.6, 3.0])
def test_inverses(M):
    for g in (1.4, 1.3):
        assert mach_from_pressure_ratio(stagnation_pressure_ratio(M, g), g) == pytest.approx(M)
        A = float(area_ratio(M, g))
        assert mach_from_area_ratio(A, g, supersonic=M > 1) == pytest.approx(M, rel=1e-9)


def test_mfp_peaks_at_sonic():
    # the mass flow per unit area is maximum at M = 1, so MFP(M) / MFP(1) = A*/A
    M = np.linspace(0.05, 3.0, 400)
    mfp = mass_flow_parameter(M, AIR)
    assert M[np.argmax(mfp)] == pytest.approx(1.0, abs=0.01)
    assert np.allclose(mfp / mass_flow_parameter(1.0, AIR), 1.0 / area_ratio(M, AIR.gamma))


def test_choked_mfp_value():
    # closed form at M = 1: sqrt(g/R) ((g+1)/2)^(-(g+1)/(2(g-1))) = 0.040418 for g = 1.4, R = 287
    from propulsion.gas import Gas

    air = Gas(cp=287.0 * 3.5, gamma=1.4)
    assert mass_flow_parameter(1.0, air) == pytest.approx(
        np.sqrt(1.4 / 287.0) * 1.2**-3.0, rel=1e-12
    )
    assert mass_flow_parameter(1.0, air) == pytest.approx(0.040418, abs=1e-6)


def test_entropy_isentropic_is_zero():
    # an isentropic compression T2/T1 = (P2/P1)^((g-1)/g) has ds = 0
    T2 = 288.15 * 20.0 ** (0.4 / 1.4)
    assert entropy_change(AIR, 288.15, 1e5, T2, 2e6) == pytest.approx(0.0, abs=1e-10)
