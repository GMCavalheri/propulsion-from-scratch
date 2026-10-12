"""Calibrated models of the CFM56-7B26/3 and LEAP-1B28, built from published data.

What is data and what is assumed (see docs/validation-report.md):

- **Data** (validation/reference_data): bypass ratio, overall pressure ratio and rated thrust
  at sea-level static ISA from the ICAO Engine Emissions Databank; take-off fuel flow from the
  same databank is used for one calibration.
- **Assumptions**: component quality ``ENGINE_COMPONENTS`` (the same for both engines), booster
  pressure ratio 1.6, convergent nozzles, no cooling or customer bleed flows, the textbook gas
  properties of ``propulsion.gas``.
- **Choices**: the fan pressure ratio is the one of minimum take-off TSFC for the given bypass
  ratio and core (Lesson 4); the burner exit temperature Tt4 is then calibrated so the model's
  take-off fuel flow equals the ICAO value. Without cooling flows this Tt4 is an
  *uncooled-equivalent* temperature, lower than a real combustor exit temperature.

Everything else (part-power fuel flows, spool speeds, turbine temperatures, lapse rates) is a
prediction of the off-design model.
"""

from __future__ import annotations

from functools import cache

from scipy.optimize import brentq

from propulsion import trade_studies
from propulsion.component_models import Components
from propulsion.flight import FlightCondition
from propulsion.off_design_performance import TurbofanEngine
from propulsion.turbofan_model import turbofan

from reference import icao

SLS = FlightCondition.sea_level_static()
PI_CL = 1.6  # booster (LPC) pressure ratio: assumption
# Assumption: polytropic efficiency 0.92 for fan, compressors and turbines (upper end of
# current technology); losses otherwise as Components.modern().
ENGINE_COMPONENTS = Components.modern().with_(e_f=0.92, e_c=0.92, e_t=0.92)
ENGINES = ("CFM56-7B26/3", "LEAP-1B28")
_KW = {"components": ENGINE_COMPONENTS, "core_nozzle": "convergent", "fan_nozzle": "convergent"}


def best_fan_pressure_ratio(alpha: float, pi_c: float, Tt4: float) -> float:
    """Fan pressure ratio of minimum sea-level-static TSFC for this core."""
    return trade_studies.best_fan_pressure_ratio(SLS, alpha, pi_c, Tt4, pi_cL=PI_CL, **_KW)


@cache
def calibrated_engine(name: str) -> TurbofanEngine:
    """Engine sized at its ICAO rating, Tt4 calibrated to the ICAO take-off fuel flow."""
    d = icao(name)
    alpha, pi_c, F = d["bpr"], d["opr"], d["rated_thrust"]

    def excess_fuel(Tt4):
        pi_f = best_fan_pressure_ratio(alpha, pi_c, Tt4)
        p = turbofan(SLS, alpha, pi_f, pi_c, Tt4, pi_cL=PI_CL, **_KW)
        return F * float(p.tsfc) - d["ff_takeoff"]

    Tt4 = brentq(excess_fuel, 1300.0, 2000.0, xtol=1e-6)
    pi_f = best_fan_pressure_ratio(alpha, pi_c, Tt4)
    return TurbofanEngine.design(
        SLS,
        alpha=alpha,
        pi_f=pi_f,
        pi_c=pi_c,
        Tt4=Tt4,
        pi_cL=PI_CL,
        thrust=F,
        components=ENGINE_COMPONENTS,
    )
