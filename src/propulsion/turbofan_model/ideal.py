"""Closed-form results for the *ideal* separate-exhaust turbofan (one perfect gas, isentropic
components, f << 1, both nozzles fully expanded), after Mattingly, *Elements of Propulsion*,
2nd ed., Sec. 5.9-5.10. Here tau_c is the temperature ratio of the *whole* core compression
(fan + compressors) and tau_lambda = Tt4 / T0.

    (V9/a0)^2  = 2/(g-1) [tau_lambda - tau_r (tau_c - 1 + alpha (tau_f - 1))
                          - tau_lambda/(tau_r tau_c)]
    (V19/a0)^2 = 2/(g-1) (tau_r tau_f - 1)

Optimum bypass ratio (minimum TSFC at fixed pi_c, pi_f, Tt4): moving bypass air at the margin
is worth it until V9 - V0 = (V19 - V0)/2, which gives

    alpha* = [tau_lambda - tau_r (tau_c - 1) - tau_lambda/(tau_r tau_c)
              - (sqrt(tau_r tau_f - 1) + sqrt(tau_r - 1))^2 / 4] / (tau_r (tau_f - 1))

Optimum fan pressure ratio (minimum TSFC at fixed alpha): the two jets are equally fast,
V19 = V9, which gives

    tau_f* = [tau_lambda - tau_r (tau_c - 1) - tau_lambda/(tau_r tau_c) + alpha tau_r + 1]
             / (tau_r (1 + alpha))
"""

from __future__ import annotations

import numpy as np

from ..flight import FlightCondition
from ..gas import AIR, Gas


def _taus(flight, pi_f, pi_c, Tt4, gas):
    k = (gas.gamma - 1.0) / gas.gamma
    tau_r = flight.tau_r(gas)
    tau_f = np.asarray(pi_f, dtype=float) ** k
    tau_c = np.asarray(pi_c, dtype=float) ** k
    tau_lambda = np.asarray(Tt4, dtype=float) / flight.T0
    return tau_r, tau_f, tau_c, tau_lambda


def ideal_jet_velocities(flight: FlightCondition, alpha, pi_f, pi_c, Tt4, gas: Gas = AIR):
    """(V9, V19) [m/s] of the ideal turbofan."""
    g = gas.gamma
    tau_r, tau_f, tau_c, tau_lambda = _taus(flight, pi_f, pi_c, Tt4, gas)
    a0 = gas.speed_of_sound(flight.T0)
    core = tau_lambda - tau_r * (tau_c - 1.0 + alpha * (tau_f - 1.0)) - tau_lambda / (tau_r * tau_c)
    V9 = a0 * np.sqrt(2.0 / (g - 1.0) * core)
    V19 = a0 * np.sqrt(2.0 / (g - 1.0) * (tau_r * tau_f - 1.0))
    return V9, V19


def optimum_bypass_ratio(flight: FlightCondition, pi_f, pi_c, Tt4, gas: Gas = AIR):
    """Bypass ratio of minimum TSFC for the ideal turbofan."""
    tau_r, tau_f, tau_c, tau_lambda = _taus(flight, pi_f, pi_c, Tt4, gas)
    jets = 0.25 * (np.sqrt(tau_r * tau_f - 1.0) + np.sqrt(tau_r - 1.0)) ** 2
    available = tau_lambda - tau_r * (tau_c - 1.0) - tau_lambda / (tau_r * tau_c)
    return (available - jets) / (tau_r * (tau_f - 1.0))


def optimum_fan_pressure_ratio(flight: FlightCondition, alpha, pi_c, Tt4, gas: Gas = AIR):
    """Fan pressure ratio of minimum TSFC for the ideal turbofan at bypass ratio ``alpha``."""
    tau_r, _, tau_c, tau_lambda = _taus(flight, 1.0, pi_c, Tt4, gas)
    available = tau_lambda - tau_r * (tau_c - 1.0) - tau_lambda / (tau_r * tau_c)
    tau_f = (available + alpha * tau_r + 1.0) / (tau_r * (1.0 + alpha))
    return tau_f ** (gas.gamma / (gas.gamma - 1.0))
