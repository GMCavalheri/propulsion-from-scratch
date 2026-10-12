"""Parametric (on-design) analysis of the non-ideal single-spool turbojet.

This is the ideal analysis of ``brayton_cycle.ideal_turbojet`` with every idealisation
removed one by one (Mattingly, *Elements of Propulsion*, 2nd ed., Sec. 7.3):

- inlet loses total pressure: pi_d = pi_d_max * eta_r(M0)            (``inlet``)
- compressor and turbine have polytropic efficiencies e_c, e_t        (``turbomachinery``)
- burner loses pressure (pi_b) and burns incompletely (eta_b)         (``burner``)
- the fuel mass is kept: the turbine and nozzle pass (1 + f) mdot0
- shaft losses: eta_m (1 + f) cpt (Tt4 - Tt5) = cpc (Tt3 - Tt2)
- hot-section gas properties (cpt, gamma_t) differ from the cold section's
- the nozzle loses pressure (pi_n) and may be convergent (under-expanded)  (``nozzle``)

With ``Components()`` (all ideal), ``hot=AIR`` and ``include_fuel_mass=False`` it reduces
exactly to the ideal turbojet.
"""

from __future__ import annotations

import numpy as np

from ..brayton_cycle.performance import CyclePerformance, Station
from ..flight import FlightCondition
from ..gas import AIR, COMBUSTION_GAS, H_PR_JET_A, Gas
from .burner import fuel_air_ratio
from .components import Components
from .inlet import inlet_pressure_ratio
from .nozzle import nozzle_exit
from .turbomachinery import (
    compressor_isentropic_efficiency,
    compressor_tau,
    turbine_isentropic_efficiency,
    turbine_pi,
)


def turbojet(
    flight: FlightCondition,
    pi_c,
    Tt4,
    components: Components = Components(),  # noqa: B008 (frozen dataclass)
    cold: Gas = AIR,
    hot: Gas = COMBUSTION_GAS,
    h_PR: float = H_PR_JET_A,
    nozzle: str = "ideal",
    include_fuel_mass: bool = True,
) -> CyclePerformance:
    """Non-ideal turbojet performance at compressor pressure ratio ``pi_c`` and burner exit
    temperature ``Tt4`` [K]. Broadcasts over ``pi_c`` and ``Tt4``."""
    c = components
    pi_c = np.asarray(pi_c, dtype=float)
    Tt4 = np.asarray(Tt4, dtype=float)
    T0, P0 = flight.T0, flight.P0
    V0 = flight.V0(cold)

    # inlet
    Tt2 = flight.Tt0(cold)
    pi_d = inlet_pressure_ratio(flight.M0, c.pi_d_max, c.inlet_shock_losses)
    Pt2 = flight.Pt0(cold) * pi_d
    # compressor
    tau_c = compressor_tau(pi_c, cold.gamma, c.e_c)
    Tt3, Pt3 = Tt2 * tau_c, Pt2 * pi_c
    # burner
    f = fuel_air_ratio(Tt3, Tt4, cold, hot, h_PR, c.eta_b, include_fuel_mass)
    m = 1.0 + f if include_fuel_mass else 1.0  # turbine/nozzle mass flow over inlet flow
    Pt4 = Pt3 * c.pi_b
    # turbine: drives the compressor through a shaft of efficiency eta_m
    Tt5 = Tt4 - cold.cp * (Tt3 - Tt2) / (c.eta_m * m * hot.cp)
    tau_t = Tt5 / Tt4
    with np.errstate(invalid="ignore"):
        pi_t = turbine_pi(tau_t, hot.gamma, c.e_t)
    Pt5 = Pt4 * pi_t
    # nozzle
    ex = nozzle_exit(Pt5 * c.pi_n, Tt5, P0, hot, nozzle)
    ok = (f > 0) & (tau_t > 0)
    V9 = np.where(ok, ex.V9, np.nan)
    specific_thrust = ex.gross_thrust(m, P0, hot.R) - V0
    specific_thrust = np.where(ok, specific_thrust, np.nan)

    ke = 0.5 * (m * V9**2 - V0**2)  # kinetic-energy gain per unit inlet air flow
    with np.errstate(divide="ignore", invalid="ignore"):
        tsfc = f / specific_thrust
        eta_thermal = ke / (f * h_PR)
        eta_propulsive = np.where(flight.M0 > 0, V0 * specific_thrust / ke, 0.0)

    stations = {
        "0": Station(np.asarray(T0), np.asarray(P0), cold, static=True),
        "2": Station(Tt2, Pt2, cold),
        "3": Station(Tt3, Pt3, cold),
        "4": Station(Tt4, Pt4, hot),
        "5": Station(Tt5, Pt5, hot),
        "9": Station(ex.T9, ex.P9, hot, static=True),
    }
    return CyclePerformance(
        specific_thrust=specific_thrust,
        tsfc=tsfc,
        f=f,
        eta_thermal=eta_thermal,
        eta_propulsive=eta_propulsive,
        eta_overall=eta_thermal * eta_propulsive,
        V0=V0,
        V9=V9,
        stations=stations,
        extras={
            "pi_d": pi_d,
            "tau_c": tau_c,
            "tau_t": tau_t,
            "pi_t": pi_t,
            "eta_c": compressor_isentropic_efficiency(pi_c, cold.gamma, c.e_c),
            "eta_t": turbine_isentropic_efficiency(tau_t, hot.gamma, c.e_t),
            "M9": ex.M9,
            "P9": ex.P9,
        },
    )
