"""Parametric trade studies on the on-design turbofan (Phase 5).

The cycle of Phase 3 has four main design variables: bypass ratio alpha, fan pressure ratio
pi_f, overall pressure ratio pi_c and burner exit temperature Tt4. For a given core, the fan
pressure ratio has an optimum (Lesson 4), so trade studies sweep (alpha, pi_c, Tt4) and give
each point its best fan. Two proxies put a price on what the fuel saving costs:

- **size**: fan diameter from the corrected flow at an assumed fan-face Mach number;
- **jet noise**: Lighthill's eighth-power law (M. J. Lighthill, Proc. R. Soc. A 211, 1952):
  the acoustic power of a jet scales as rho A V^8, i.e. as mdot V^7 at fixed density. Summed
  over the two streams this ranks designs; it is not a noise prediction (no fan, turbine or
  shear-layer noise, no installation or propagation effects).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize_scalar

from ..brayton_cycle.performance import CyclePerformance
from ..component_models.components import Components
from ..flight import FlightCondition
from ..gas import AIR, mass_flow_parameter
from ..turbofan_model import turbofan


def best_fan_pressure_ratio(
    flight: FlightCondition,
    alpha: float,
    pi_c: float,
    Tt4: float,
    pi_cL: float = 1.0,
    pi_f_max: float = 4.0,
    **cycle_kwargs,
) -> float:
    """Fan pressure ratio of minimum TSFC for one core (alpha, pi_c, Tt4) at ``flight``.

    A grid search first (beyond the optimum the core runs out of energy and TSFC is
    undefined), then a bounded refinement around the best grid point. Returns NaN when no fan
    pressure ratio gives thrust.
    """
    upper = min(pi_f_max, pi_c / max(pi_cL, 1.0) / 1.05)
    grid = np.geomspace(1.05, upper, 300)
    tsfc = turbofan(flight, alpha, grid, pi_c, Tt4, pi_cL=pi_cL, **cycle_kwargs).tsfc
    if np.all(np.isnan(tsfc)):
        return np.nan
    i = int(np.nanargmin(tsfc))
    lo, hi = grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]

    def f(pi_f):
        s = float(turbofan(flight, alpha, pi_f, pi_c, Tt4, pi_cL=pi_cL, **cycle_kwargs).tsfc)
        return s if np.isfinite(s) else np.inf

    return float(minimize_scalar(f, bounds=(lo, hi), method="bounded", options={"xatol": 1e-8}).x)


@dataclass(frozen=True)
class Sweep:
    """Result of :func:`sweep`: inputs and outputs on the same grid (arrays of equal shape)."""

    alpha: np.ndarray
    pi_c: np.ndarray
    Tt4: np.ndarray
    pi_f: np.ndarray
    specific_thrust: np.ndarray
    tsfc: np.ndarray
    eta_thermal: np.ndarray
    eta_propulsive: np.ndarray
    eta_overall: np.ndarray
    Tt3: np.ndarray
    Pt3: np.ndarray


def sweep(
    flight: FlightCondition,
    alpha,
    pi_c,
    Tt4,
    pi_cL: float = 1.0,
    components: Components = Components.modern(),  # noqa: B008 (frozen dataclass)
    **cycle_kwargs,
) -> Sweep:
    """Evaluate every combination of ``alpha`` x ``pi_c`` x ``Tt4``, each with its best fan.

    Inputs are broadcast with ``numpy.meshgrid(..., indexing="ij")``; scalars are allowed.
    """
    A, PC, T = np.meshgrid(
        np.atleast_1d(alpha).astype(float),
        np.atleast_1d(pi_c).astype(float),
        np.atleast_1d(Tt4).astype(float),
        indexing="ij",
    )
    kw = {"components": components, **cycle_kwargs}
    PF = np.empty_like(A)
    for idx in np.ndindex(A.shape):
        PF[idx] = best_fan_pressure_ratio(flight, A[idx], PC[idx], T[idx], pi_cL, **kw)
    p = turbofan(flight, A, PF, PC, T, pi_cL=pi_cL, **kw)
    return Sweep(
        alpha=A,
        pi_c=PC,
        Tt4=T,
        pi_f=PF,
        specific_thrust=p.specific_thrust,
        tsfc=p.tsfc,
        eta_thermal=p.eta_thermal,
        eta_propulsive=p.eta_propulsive,
        eta_overall=p.eta_overall,
        Tt3=p.stations["3"].T,
        Pt3=p.stations["3"].P,
    )


def fan_diameter(
    mdot0, flight: FlightCondition, M2: float = 0.6, hub_tip: float = 0.3, pi_d: float = 1.0
):
    """Fan tip diameter [m] that passes ``mdot0`` [kg/s] at fan-face Mach ``M2``.

    Annulus area A = mdot0 sqrt(Tt2) / (Pt2 MFP(M2)) = (pi/4) D^2 (1 - hub_tip^2). The fan-face
    Mach number and hub/tip ratio are assumptions (0.6 and 0.3 are typical design values).
    """
    Pt2 = flight.Pt0(AIR) * pi_d
    area = np.asarray(mdot0) * np.sqrt(flight.Tt0(AIR)) / (Pt2 * mass_flow_parameter(M2, AIR))
    return np.sqrt(4.0 * area / (np.pi * (1.0 - hub_tip**2)))


def jet_noise_index(perf: CyclePerformance, thrust: float):
    """Relative jet-noise level [dB] of an engine sized for ``thrust`` [N]: 10 log10(sum of
    mdot V^7 over the core and bypass streams), from Lighthill's eighth-power law.

    Only *differences* between designs are meaningful.
    """
    alpha = np.asarray(perf.extras.get("alpha", 0.0), dtype=float)
    mdot0 = thrust / np.asarray(perf.specific_thrust)
    core = mdot0 / (1.0 + alpha) * (1.0 + np.asarray(perf.f)) * np.asarray(perf.V9) ** 7
    fan = mdot0 * alpha / (1.0 + alpha) * np.asarray(perf.extras.get("V19", 0.0)) ** 7
    return 10.0 * np.log10(core + fan)
