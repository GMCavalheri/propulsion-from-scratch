"""Calorically perfect gas: constant cp and gamma, h = cp T, P = rho R T.

Cycle analysis in the style of Mattingly (*Elements of Propulsion*, 2nd ed., 2006, Ch. 7) uses
two such gases: one for the cold section (inlet, fan, compressors) and one for the hot section
(burner exit onwards), whose larger cp and smaller gamma account for the higher temperature and
the combustion products. The default property values below are *modelling assumptions* taken
from that text's worked examples, not measurements of any engine.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Gas:
    """A calorically perfect gas with constant ``cp`` [J/(kg K)] and ratio of heats ``gamma``."""

    cp: float
    gamma: float

    @property
    def R(self) -> float:
        """Gas constant R = cp (gamma - 1) / gamma [J/(kg K)]."""
        return self.cp * (self.gamma - 1.0) / self.gamma

    @property
    def cv(self) -> float:
        return self.cp / self.gamma

    def speed_of_sound(self, T):
        return np.sqrt(self.gamma * self.R * np.asarray(T, dtype=float))


# Assumptions (Mattingly 2006, Ch. 7 examples): cold air cp = 1.004 kJ/(kg K), gamma = 1.4;
# hot gas cp = 1.239 kJ/(kg K), gamma = 1.3; Jet-A heating value h_PR = 42,800 kJ/kg.
AIR = Gas(cp=1004.0, gamma=1.4)
COMBUSTION_GAS = Gas(cp=1239.0, gamma=1.3)
H_PR_JET_A = 42.8e6  # J/kg


def entropy_change(gas: Gas, T1, P1, T2, P2):
    """s2 - s1 = cp ln(T2/T1) - R ln(P2/P1) [J/(kg K)] (Gibbs equation for a perfect gas).

    Works with static or stagnation states alike, as long as both ends use the same kind:
    the stagnation state of a flow has the same entropy as its static state.
    """
    return gas.cp * np.log(np.asarray(T2) / T1) - gas.R * np.log(np.asarray(P2) / P1)
