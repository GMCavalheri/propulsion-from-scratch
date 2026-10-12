"""Burner (combustor) energy balance."""

from __future__ import annotations

import numpy as np

from ..gas import Gas

T_REF = 298.15  # K, reference temperature of the fuel heating value h_PR


def fuel_air_ratio(
    Tt3,
    Tt4,
    cold: Gas,
    hot: Gas,
    h_PR: float,
    eta_b: float = 1.0,
    include_fuel_mass=True,
    T_ref: float = T_REF,
):
    """Fuel/air ratio f = mdot_f / mdot_air that heats air from ``Tt3`` to ``Tt4``.

    Steady-flow energy balance, with the fuel entering at the reference temperature and its
    heating value h_PR released at efficiency eta_b. The heating value is defined for reactants
    and products at T_ref = 298.15 K, so both gases must measure enthalpy from that same datum,
    h = cp (T - T_ref):

        (1 + f) cpt (Tt4 - T_ref) - cpc (Tt3 - T_ref) = eta_b h_PR f
        =>  f = [cpt (Tt4 - T_ref) - cpc (Tt3 - T_ref)] / [eta_b h_PR - cpt (Tt4 - T_ref)]

    Mattingly (2006, Ch. 7) writes the same balance with h = cp T for each gas, i.e. each
    measured from 0 K. When cpt > cpc that counts an extra (cpt - cpc) T_ref of heat, about
    70 kJ/kg (6-10 % more fuel at typical burner temperatures). Pass ``T_ref=0`` to reproduce
    his form. When cpt = cpc the datum cancels in the numerator.

    With ``include_fuel_mass=False`` the (1 + f) is dropped, as in the ideal analysis:
    f = [cpt (Tt4 - T_ref) - cpc (Tt3 - T_ref)] / (eta_b h_PR).
    """
    h4 = hot.cp * (np.asarray(Tt4, dtype=float) - T_ref)
    h3 = cold.cp * (np.asarray(Tt3, dtype=float) - T_ref)
    return (h4 - h3) / (eta_b * h_PR - (h4 if include_fuel_mass else 0.0))
