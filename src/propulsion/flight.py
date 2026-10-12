"""Flight condition (free stream, station 0) shared by every cycle model."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .atmosphere import isa
from .gas import AIR, Gas


@dataclass(frozen=True)
class FlightCondition:
    """Free-stream static temperature ``T0`` [K], pressure ``P0`` [Pa] and Mach number ``M0``."""

    M0: float
    T0: float
    P0: float

    @classmethod
    def at_altitude(
        cls, altitude: float, M0: float, dT: float = 0.0, geopotential: bool = False
    ) -> FlightCondition:
        """ISA (+dT) free stream at ``altitude`` [m]. Flight levels: ``geopotential=True``."""
        a = isa(altitude, dT=dT, geopotential=geopotential)
        return cls(M0=M0, T0=float(a.T), P0=float(a.P))

    @classmethod
    def sea_level_static(cls, dT: float = 0.0) -> FlightCondition:
        return cls.at_altitude(0.0, 0.0, dT=dT)

    def a0(self, gas: Gas = AIR):
        """Free-stream speed of sound [m/s] in the cycle's cold gas."""
        return gas.speed_of_sound(self.T0)

    def V0(self, gas: Gas = AIR):
        """Flight speed [m/s]."""
        return self.M0 * self.a0(gas)

    def tau_r(self, gas: Gas = AIR):
        """Ram temperature ratio Tt0 / T0."""
        return 1.0 + 0.5 * (gas.gamma - 1.0) * np.asarray(self.M0, dtype=float) ** 2

    def pi_r(self, gas: Gas = AIR):
        """Ram pressure ratio Pt0 / P0 (isentropic)."""
        return self.tau_r(gas) ** (gas.gamma / (gas.gamma - 1.0))

    def Tt0(self, gas: Gas = AIR):
        return self.T0 * self.tau_r(gas)

    def Pt0(self, gas: Gas = AIR):
        return self.P0 * self.pi_r(gas)
