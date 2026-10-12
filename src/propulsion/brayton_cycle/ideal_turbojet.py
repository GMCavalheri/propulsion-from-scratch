"""Parametric (on-design) analysis of the ideal turbojet.

Assumptions (Mattingly, *Elements of Propulsion*, 2nd ed., Sec. 5.6): every component is
isentropic except the burner, which adds heat at constant stagnation pressure; one calorically
perfect gas throughout; the nozzle expands fully to ambient pressure (P9 = P0); the fuel mass
is small compared with the air mass (f << 1 is neglected in the momentum and energy balances,
but reported). With

    tau_r = 1 + (g-1)/2 M0^2,   tau_c = pi_c^((g-1)/g),   tau_lambda = Tt4 / T0

the turbine drives the compressor (tau_r (tau_c - 1) = tau_lambda (1 - tau_t)) and

    (V9/a0)^2 = 2/(g-1) * tau_lambda / (tau_r tau_c) * (tau_r tau_c tau_t - 1)
    F/mdot0   = a0 (V9/a0 - M0)
    f         = cp T0 (tau_lambda - tau_r tau_c) / h_PR
    eta_th    = 1 - 1/(tau_r tau_c),   eta_p = 2 M0 / (V9/a0 + M0)

Everything broadcasts, so a whole sweep of ``pi_c`` or ``Tt4`` is a single call.
"""

from __future__ import annotations

import numpy as np

from ..flight import FlightCondition
from ..gas import AIR, H_PR_JET_A, Gas
from .performance import CyclePerformance, Station


def ideal_turbojet(
    flight: FlightCondition,
    pi_c,
    Tt4,
    gas: Gas = AIR,
    h_PR: float = H_PR_JET_A,
) -> CyclePerformance:
    """Ideal turbojet performance at compressor pressure ratio ``pi_c`` and burner exit
    temperature ``Tt4`` [K]. Returns NaN thrust where the cycle cannot run (Tt4 below Tt3)."""
    g, cp = gas.gamma, gas.cp
    pi_c = np.asarray(pi_c, dtype=float)
    Tt4 = np.asarray(Tt4, dtype=float)
    T0, P0, M0 = flight.T0, flight.P0, flight.M0
    a0 = gas.speed_of_sound(T0)
    k = (g - 1.0) / g

    tau_r = flight.tau_r(gas)
    pi_r = flight.pi_r(gas)
    tau_c = pi_c**k
    tau_lambda = Tt4 / T0
    tau_t = 1.0 - tau_r / tau_lambda * (tau_c - 1.0)
    pi_t = tau_t ** (1.0 / k)

    with np.errstate(invalid="ignore"):
        V9_a0 = np.sqrt(
            2.0 / (g - 1.0) * tau_lambda / (tau_r * tau_c) * (tau_r * tau_c * tau_t - 1)
        )
    f = cp * T0 * (tau_lambda - tau_r * tau_c) / h_PR
    V9_a0 = np.where(f > 0.0, V9_a0, np.nan)

    specific_thrust = a0 * (V9_a0 - M0)
    eta_thermal = 1.0 - 1.0 / (tau_r * tau_c)
    with np.errstate(divide="ignore", invalid="ignore"):
        tsfc = np.where(specific_thrust > 0, f / specific_thrust, np.nan)  # no thrust, no TSFC
        # static (M0 = 0): no thrust power, so eta_p = 0 even when V9 = 0 too
        eta_propulsive = np.where(M0 > 0, 2.0 * M0 / (V9_a0 + M0), 0.0)

    Tt0, Pt0 = T0 * tau_r, P0 * pi_r
    Tt3, Pt3 = Tt0 * tau_c, Pt0 * pi_c
    Tt5, Pt5 = Tt4 * tau_t, Pt3 * pi_t
    T9 = Tt5 / (Pt5 / P0) ** k
    stations = {
        "0": Station(np.asarray(T0), np.asarray(P0), gas, static=True),
        "2": Station(Tt0, Pt0, gas),
        "3": Station(Tt3, Pt3, gas),
        "4": Station(Tt4, Pt3, gas),
        "5": Station(Tt5, Pt5, gas),
        "9": Station(T9, np.asarray(P0), gas, static=True),
    }
    return CyclePerformance(
        specific_thrust=specific_thrust,
        tsfc=tsfc,
        f=f,
        eta_thermal=eta_thermal,
        eta_propulsive=eta_propulsive,
        eta_overall=eta_thermal * eta_propulsive,
        V0=M0 * a0,
        V9=V9_a0 * a0,
        stations=stations,
        extras={"tau_r": tau_r, "tau_c": tau_c, "tau_t": tau_t, "tau_lambda": tau_lambda},
    )


def optimum_compressor_pressure_ratio(flight: FlightCondition, Tt4, gas: Gas = AIR):
    """Compressor pressure ratio of maximum specific thrust: tau_c* = sqrt(tau_lambda) / tau_r.

    Found by setting d(V9/a0)^2 / d(tau_c) = 0 (Mattingly 2006, Sec. 5.6). At this point the
    static nozzle-exit temperature equals the compressor-exit temperature, T9 = Tt3, the open-
    cycle analogue of T2 = T4 at the work optimum of the closed Brayton cycle.
    """
    tau_lambda = np.asarray(Tt4, dtype=float) / flight.T0
    tau_c = np.sqrt(tau_lambda) / flight.tau_r(gas)
    return tau_c ** (gas.gamma / (gas.gamma - 1.0))
