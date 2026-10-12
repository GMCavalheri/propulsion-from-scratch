"""Burner (combustor) energy balance."""

from __future__ import annotations

import numpy as np

from ..gas import Gas


def fuel_air_ratio(
    Tt3, Tt4, cold: Gas, hot: Gas, h_PR: float, eta_b: float = 1.0, include_fuel_mass=True
):
    """Fuel/air ratio f = mdot_f / mdot_air that heats air from ``Tt3`` to ``Tt4``.

    Steady-flow energy balance with the fuel's chemical energy released at efficiency eta_b
    (Mattingly 2006, Ch. 7):

        (1 + f) cpt Tt4 - cpc Tt3 = eta_b h_PR f
        =>  f = (cpt Tt4 - cpc Tt3) / (eta_b h_PR - cpt Tt4)

    With ``include_fuel_mass=False`` the (1 + f) is dropped, as in the ideal analysis:
    f = (cpt Tt4 - cpc Tt3) / (eta_b h_PR).
    """
    num = hot.cp * np.asarray(Tt4, dtype=float) - cold.cp * np.asarray(Tt3, dtype=float)
    den = eta_b * h_PR - (hot.cp * np.asarray(Tt4, dtype=float) if include_fuel_mass else 0.0)
    return num / den
