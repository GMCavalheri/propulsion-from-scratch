"""Parametric (on-design) analysis of a two-spool, separate-exhaust turbofan.

Layout and station numbers (SAE ARP755 / Mattingly):

    0 free stream -> 2 fan face -> fan -> 13 fan exit -> 19 bypass (fan) nozzle exit
                                       \\-> core: 13 -> LPC (booster) -> 25 -> HPC -> 3
                                           -> burner -> 4 -> HPT -> 45 -> LPT -> 5 -> 9

The low-pressure spool carries the fan and the booster and is driven by the LPT; the
high-pressure spool carries the HPC and is driven by the HPT. With bypass ratio
alpha = mdot_bypass / mdot_core, per unit *core* air flow (Mattingly, *Elements of Propulsion*,
2nd ed., Ch. 7, extended with a booster):

    HP spool:  eta_mH (1 + f) cpt (Tt4 - Tt45) = cpc (Tt3 - Tt25)
    LP spool:  eta_mL (1 + f) cpt (Tt45 - Tt5) = cpc [(1 + alpha)(Tt13 - Tt2) + (Tt25 - Tt13)]

Thrust is the sum of the two streams, each with its own nozzle, quoted per unit of *total*
inlet air flow mdot0 = (1 + alpha) mdot_core:

    F/mdot0 = [ Fg_core/mdot_c - V0  +  alpha (Fg_fan/mdot_b - V0) ] / (1 + alpha)

and TSFC = f / ((1 + alpha) F/mdot0), with f the fuel/air ratio of the core.
"""

from __future__ import annotations

import numpy as np

from ..brayton_cycle.performance import CyclePerformance, Station
from ..component_models.burner import fuel_air_ratio
from ..component_models.components import Components
from ..component_models.inlet import inlet_pressure_ratio
from ..component_models.nozzle import nozzle_exit
from ..component_models.turbomachinery import compressor_tau, turbine_pi
from ..flight import FlightCondition
from ..gas import AIR, COMBUSTION_GAS, H_PR_JET_A, Gas


def turbofan(
    flight: FlightCondition,
    alpha,
    pi_f,
    pi_c,
    Tt4,
    pi_cL=1.0,
    components: Components = Components(),  # noqa: B008 (frozen dataclass)
    cold: Gas = AIR,
    hot: Gas = COMBUSTION_GAS,
    h_PR: float = H_PR_JET_A,
    core_nozzle: str = "ideal",
    fan_nozzle: str = "ideal",
    include_fuel_mass: bool = True,
) -> CyclePerformance:
    """Two-spool separate-exhaust turbofan.

    alpha  bypass ratio;  pi_f  fan pressure ratio (bypass and core side alike)
    pi_c   overall pressure ratio of the core, Pt3/Pt2 (fan x booster x HPC)
    pi_cL  booster (LPC) pressure ratio; the HPC ratio is pi_c / (pi_f pi_cL)
    Tt4    burner exit temperature [K]

    All of them broadcast. ``extras`` holds the core and bypass thrust (per unit total inlet
    flow), both jet velocities, spool temperature ratios and the HPC pressure ratio.
    """
    c = components
    alpha = np.asarray(alpha, dtype=float)
    pi_f = np.asarray(pi_f, dtype=float)
    pi_c = np.asarray(pi_c, dtype=float)
    pi_cL = np.asarray(pi_cL, dtype=float)
    Tt4 = np.asarray(Tt4, dtype=float)
    P0 = flight.P0
    V0 = flight.V0(cold)
    pi_cH = pi_c / (pi_f * pi_cL)

    # inlet and fan
    Tt2 = flight.Tt0(cold)
    pi_d = inlet_pressure_ratio(flight.M0, c.pi_d_max, c.inlet_shock_losses)
    Pt2 = flight.Pt0(cold) * pi_d
    Tt13 = Tt2 * compressor_tau(pi_f, cold.gamma, c.e_f)
    Pt13 = Pt2 * pi_f
    # booster (LPC) and HPC
    Tt25 = Tt13 * compressor_tau(pi_cL, cold.gamma, c.e_c)
    Pt25 = Pt13 * pi_cL
    Tt3 = Tt25 * compressor_tau(pi_cH, cold.gamma, c.e_c)
    Pt3 = Pt25 * pi_cH
    # burner
    f = fuel_air_ratio(Tt3, Tt4, cold, hot, h_PR, c.eta_b, include_fuel_mass)
    m = 1.0 + f if include_fuel_mass else 1.0
    Pt4 = Pt3 * c.pi_b
    # HP turbine drives the HPC; LP turbine drives the fan (all flow) and the booster (core)
    Tt45 = Tt4 - cold.cp * (Tt3 - Tt25) / (c.eta_m * m * hot.cp)
    lp_work = cold.cp * ((1.0 + alpha) * (Tt13 - Tt2) + (Tt25 - Tt13))
    Tt5 = Tt45 - lp_work / (c.eta_m * m * hot.cp)
    tau_tH, tau_tL = Tt45 / Tt4, Tt5 / Tt45
    with np.errstate(invalid="ignore"):
        pi_tH = turbine_pi(tau_tH, hot.gamma, c.e_t)
        pi_tL = turbine_pi(tau_tL, hot.gamma, c.e_t)
    Pt45 = Pt4 * pi_tH
    Pt5 = Pt45 * pi_tL

    core = nozzle_exit(Pt5 * c.pi_n, Tt5, P0, hot, core_nozzle)
    fan = nozzle_exit(Pt13 * c.pi_fn, Tt13, P0, cold, fan_nozzle)
    ok = (f > 0) & (Tt5 > 0) & (Tt45 > 0)
    V9 = np.where(ok, core.V9, np.nan)
    V19 = fan.V9
    F_core = (core.gross_thrust(m, P0, hot.R) - V0) / (1.0 + alpha)
    F_fan = alpha * (fan.gross_thrust(1.0, P0, cold.R) - V0) / (1.0 + alpha)
    F_core = np.where(ok, F_core, np.nan)
    specific_thrust = F_core + F_fan

    ke = 0.5 * (m * V9**2 + alpha * V19**2 - (1.0 + alpha) * V0**2)  # per unit core flow
    with np.errstate(divide="ignore", invalid="ignore"):
        tsfc = np.where(specific_thrust > 0, f / ((1.0 + alpha) * specific_thrust), np.nan)
        eta_thermal = ke / (f * h_PR)
        eta_propulsive = np.where(flight.M0 > 0, V0 * (1.0 + alpha) * specific_thrust / ke, 0.0)

    stations = {
        "0": Station(np.asarray(flight.T0), np.asarray(P0), cold, static=True),
        "2": Station(Tt2, Pt2, cold),
        "13": Station(Tt13, Pt13, cold),
        "19": Station(fan.T9, fan.P9, cold, static=True),
        "25": Station(Tt25, Pt25, cold),
        "3": Station(Tt3, Pt3, cold),
        "4": Station(Tt4, Pt4, hot),
        "45": Station(Tt45, Pt45, hot),
        "5": Station(Tt5, Pt5, hot),
        "9": Station(core.T9, core.P9, hot, static=True),
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
            "alpha": alpha,
            "specific_thrust_core": F_core,
            "specific_thrust_fan": F_fan,
            "thrust_ratio_fan": F_fan / specific_thrust,
            "V19": V19,
            "pi_cH": pi_cH,
            "tau_tH": tau_tH,
            "tau_tL": tau_tL,
            "pi_tH": pi_tH,
            "pi_tL": pi_tL,
            "M9": core.M9,
            "M19": fan.M9,
            "P9": core.P9,
            "P19": fan.P9,
        },
    )
