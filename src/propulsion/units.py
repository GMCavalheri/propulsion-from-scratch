"""Exact unit conversion factors (to SI). Internal quantities are always SI.

Sources: NIST SP 811 (2008), Appendix B — the pound-mass, pound-force, foot and knot are
defined exactly in SI.
"""

from __future__ import annotations

LB = 0.45359237  # kg per pound-mass (exact)
G0 = 9.80665  # m/s^2, standard gravity (exact)
LBF = LB * G0  # N per pound-force = 4.4482216152605 (exact)
FT = 0.3048  # m per foot (exact)
KT = 1852.0 / 3600.0  # m/s per knot (exact)
HOUR = 3600.0  # s

TSFC_LB_PER_LBF_H = LB / (LBF * HOUR)  # kg/(N s) per lb/(lbf h) ≈ 2.8325e-5


def tsfc_to_lb_per_lbf_h(tsfc: float) -> float:
    """Convert TSFC from kg/(N s) to lb/(lbf h)."""
    return tsfc / TSFC_LB_PER_LBF_H


def tsfc_from_lb_per_lbf_h(tsfc_imperial: float) -> float:
    """Convert TSFC from lb/(lbf h) to kg/(N s)."""
    return tsfc_imperial * TSFC_LB_PER_LBF_H


def tsfc_to_mg_per_n_s(tsfc: float) -> float:
    """Convert TSFC from kg/(N s) to mg/(N s), the unit common in SI textbooks."""
    return tsfc * 1e6
