import pytest

from propulsion.units import LBF, TSFC_LB_PER_LBF_H, tsfc_from_lb_per_lbf_h, tsfc_to_lb_per_lbf_h


def test_pound_force():
    # NIST SP 811 (2008), App. B: 1 lbf = 4.448 221 615 260 5 N (exact)
    assert LBF == pytest.approx(4.4482216152605, abs=1e-13)


def test_tsfc_conversion():
    # 1 lb/(lbf h) = 0.45359237 / (4.4482216152605 * 3600) kg/(N s) = 28.325 mg/(N s)
    assert TSFC_LB_PER_LBF_H == pytest.approx(2.8325e-5, rel=1e-4)
    assert tsfc_to_lb_per_lbf_h(tsfc_from_lb_per_lbf_h(0.55)) == pytest.approx(0.55)
