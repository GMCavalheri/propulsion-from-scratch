"""Exhaust nozzle: exit state and gross thrust per unit mass flow."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..gas import Gas


@dataclass(frozen=True)
class NozzleExit:
    P9: np.ndarray  # static exit pressure [Pa]
    T9: np.ndarray  # static exit temperature [K]
    M9: np.ndarray  # exit Mach number
    V9: np.ndarray  # exit velocity [m/s]

    def gross_thrust(self, mass_ratio, P0: float, R: float):
        """Gross thrust per unit *inlet* air flow: m V9 + (P9 - P0) A9 / mdot0, where
        ``mass_ratio`` m = mdot9 / mdot0 and A9 = mdot9 R T9 / (P9 V9)."""
        return mass_ratio * (self.V9 + R * self.T9 * (1.0 - P0 / self.P9) / self.V9)


def nozzle_exit(Pt9, Tt9, P0: float, gas: Gas, kind: str = "ideal") -> NozzleExit:
    """Exit state of a nozzle with inlet stagnation state (``Pt9``, ``Tt9``) [Pa, K].

    ``kind="ideal"``: convergent-divergent, fully expanded to P9 = P0.
    ``kind="convergent"``: if Pt9/P0 exceeds the critical ratio ((g+1)/2)^(g/(g-1)) the exit
    chokes at M9 = 1 and P9 > P0 (an under-expanded jet, which adds pressure thrust);
    otherwise it expands to P0.

    Returns NaN where Pt9 < P0 (the nozzle cannot discharge).
    """
    g = gas.gamma
    Pt9 = np.asarray(Pt9, dtype=float)
    Tt9 = np.asarray(Tt9, dtype=float)
    if kind == "ideal":
        P9 = np.full_like(Pt9, P0)
    elif kind == "convergent":
        critical = (0.5 * (g + 1.0)) ** (g / (g - 1.0))
        P9 = np.maximum(P0, Pt9 / critical)
    else:
        raise ValueError(f"unknown nozzle kind {kind!r}")
    ratio = np.where(Pt9 >= P9, Pt9 / P9, np.nan)
    Tt_T = ratio ** ((g - 1.0) / g)
    M9 = np.sqrt(2.0 / (g - 1.0) * (Tt_T - 1.0))
    T9 = Tt9 / Tt_T
    V9 = M9 * np.sqrt(g * gas.R * T9)
    return NozzleExit(P9=P9[()], T9=T9[()], M9=M9[()], V9=V9[()])
