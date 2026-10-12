"""Inlet (diffuser) total-pressure recovery."""

from __future__ import annotations

import numpy as np


def ram_recovery(M0):
    """Ram recovery eta_r of the military specification MIL-E-5007D, as given by Mattingly
    (*Elements of Propulsion*, 2nd ed., Ch. 6):

        eta_r = 1                                for M0 <= 1
        eta_r = 1 - 0.075 (M0 - 1)^1.35          for 1 < M0 <= 5
        eta_r = 800 / (M0^4 + 935)               for M0 > 5

    It models the shock losses of a supersonic inlet; subsonic inlets only lose pi_d_max.
    """
    M0 = np.asarray(M0, dtype=float)
    mid = 1.0 - 0.075 * np.clip(M0 - 1.0, 0.0, None) ** 1.35
    return np.where(M0 <= 1.0, 1.0, np.where(M0 <= 5.0, mid, 800.0 / (M0**4 + 935.0)))[()]


def inlet_pressure_ratio(M0, pi_d_max: float, shock_losses: bool = True):
    """pi_d = Pt2 / Pt0 = pi_d_max * eta_r(M0) (eta_r = 1 without ``shock_losses``)."""
    return pi_d_max * (ram_recovery(M0) if shock_losses else 1.0)
