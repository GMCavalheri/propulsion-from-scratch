"""Isentropic one-dimensional flow relations for a perfect gas.

Standard results (e.g. Anderson, *Modern Compressible Flow*, 3rd ed., Ch. 3 and 5):

    Tt/T  = 1 + (g-1)/2 M^2
    Pt/P  = (Tt/T)^(g/(g-1))
    A/A*  = (1/M) [2/(g+1) (1 + (g-1)/2 M^2)]^((g+1)/(2(g-1)))
    MFP   = mdot sqrt(Tt) / (Pt A) = M sqrt(g/R) (1 + (g-1)/2 M^2)^(-(g+1)/(2(g-1)))

The mass-flow parameter (MFP) is the key to off-design analysis: at a choked throat (M = 1)
it is a constant of the gas, so the corrected flow through the throat is fixed.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

from .perfect_gas import Gas


def stagnation_temperature_ratio(M, gamma: float):
    """Tt / T at Mach M."""
    M = np.asarray(M, dtype=float)
    return 1.0 + 0.5 * (gamma - 1.0) * M**2


def stagnation_pressure_ratio(M, gamma: float):
    """Pt / P at Mach M (isentropic)."""
    return stagnation_temperature_ratio(M, gamma) ** (gamma / (gamma - 1.0))


def mach_from_temperature_ratio(Tt_over_T, gamma: float):
    """Mach number from Tt / T >= 1."""
    return np.sqrt(2.0 / (gamma - 1.0) * (np.asarray(Tt_over_T, dtype=float) - 1.0))


def mach_from_pressure_ratio(Pt_over_P, gamma: float):
    """Mach number from Pt / P >= 1 (isentropic)."""
    ratio = np.asarray(Pt_over_P, dtype=float) ** ((gamma - 1.0) / gamma)
    return mach_from_temperature_ratio(ratio, gamma)


def area_ratio(M, gamma: float):
    """A / A* for isentropic flow at Mach M."""
    M = np.asarray(M, dtype=float)
    e = (gamma + 1.0) / (2.0 * (gamma - 1.0))
    return (2.0 / (gamma + 1.0) * stagnation_temperature_ratio(M, gamma)) ** e / M


def mach_from_area_ratio(A_over_Astar: float, gamma: float, supersonic: bool = False) -> float:
    """Invert A/A* for the subsonic (default) or supersonic branch."""
    if A_over_Astar < 1.0:
        raise ValueError("A/A* must be >= 1")
    if A_over_Astar == 1.0:
        return 1.0
    f = lambda M: area_ratio(M, gamma) - A_over_Astar  # noqa: E731
    return brentq(f, 1.0, 100.0) if supersonic else brentq(f, 1e-9, 1.0)


def mass_flow_parameter(M, gas: Gas):
    """MFP = mdot sqrt(Tt) / (Pt A) [kg K^0.5 / (N s)] at Mach M."""
    g = gas.gamma
    M = np.asarray(M, dtype=float)
    e = -(g + 1.0) / (2.0 * (g - 1.0))
    return M * np.sqrt(g / gas.R) * stagnation_temperature_ratio(M, g) ** e
