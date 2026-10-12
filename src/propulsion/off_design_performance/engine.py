"""Off-design performance of a fixed two-spool, separate-exhaust turbofan.

Once an engine is built, its *geometry* is frozen: the throat areas of the HP turbine nozzle
(station 4), the LP turbine nozzle (45), the core nozzle (9) and the fan nozzle (19). The cycle
of Phase 3 had free design choices (alpha, pi_f, pi_c...); off design those become unknowns, set
by the geometry. Following the method of Mattingly (*Elements of Propulsion*, 2nd ed., Ch. 8):

1. **Choked turbine nozzles.** The HPT and LPT inlet guide vanes run choked, so
   mdot sqrt(Tt)/Pt is fixed at both. With constant turbine efficiency this fixes the HPT
   pressure and temperature ratio: tau_tH = tau_tH,design.
2. **HP spool.** The HPC must absorb exactly the work the HPT supplies at that tau_tH.
3. **LP spool.** The LPT drives fan and booster; the booster work keeps a fixed proportion to the
   fan work, since both turn at the same speed: (Tt25 - Tt13) / (Tt13 - Tt2) = design value.
4. **Flow matching.** The core flow is what the choked HPT passes,
   mdot_core (1 + f) = C4 Pt4 / sqrt(Tt4); the bypass flow is what the fan nozzle passes,
   A19 MFP(M19) Pt19 / sqrt(Tt19); and the core gas must fit through the core nozzle,
   A9 MFP(M9) Pt9 / sqrt(Tt9). Their ratio fixes alpha.
5. **Constant component quality.** Polytropic efficiencies and pressure-loss ratios stay at their
   design values (a standard first approximation that ignores the map).

The unknowns (pi_f, pi_cL, pi_cH, alpha) are solved with ``scipy.optimize.root`` for each
flight condition and throttle setting (Tt4). The on-design function ``turbofan`` evaluates the
cycle, so the design point is reproduced exactly and every power balance closes by
construction. Spool speeds use the constant-work-coefficient estimate
(N / N_design)^2 = dh / dh_design for the fan (N1) and the HPC (N2).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq, root

from ..brayton_cycle.performance import CyclePerformance
from ..component_models.components import Components
from ..flight import FlightCondition
from ..gas import AIR, COMBUSTION_GAS, H_PR_JET_A, Gas, mass_flow_parameter
from ..turbofan_model import turbofan


@dataclass(frozen=True)
class OperatingPoint:
    """One solved operating point of an engine (all values physical, SI)."""

    flight: FlightCondition
    Tt4: float
    alpha: float
    pi_f: float
    pi_cL: float
    pi_cH: float
    mdot_core: float  # kg/s
    thrust: float  # N
    fuel_flow: float  # kg/s
    N1: float  # LP spool speed / design speed
    N2: float  # HP spool speed / design speed
    cycle: CyclePerformance = field(repr=False)
    converged: bool = True

    @property
    def mdot0(self) -> float:
        """Total inlet air flow [kg/s]."""
        return (1.0 + self.alpha) * self.mdot_core

    @property
    def pi_c(self) -> float:
        """Overall pressure ratio Pt3 / Pt2."""
        return self.pi_f * self.pi_cL * self.pi_cH

    @property
    def tsfc(self) -> float:
        return self.fuel_flow / self.thrust if self.thrust > 0 else np.nan

    @property
    def Tt45(self) -> float:
        """LP-turbine inlet temperature [K] (engine EGT is measured in the turbine section,
        between stations 45 and 5 depending on the engine)."""
        return float(self.cycle.stations["45"].T)

    @property
    def Tt5(self) -> float:
        """LP-turbine exit temperature [K]."""
        return float(self.cycle.stations["5"].T)

    @property
    def theta2(self) -> float:
        return float(self.cycle.stations["2"].T) / 288.15

    @property
    def delta2(self) -> float:
        return float(self.cycle.stations["2"].P) / 101325.0

    @property
    def corrected_flow(self) -> float:
        """Corrected fan-face flow mdot0 sqrt(theta2) / delta2 [kg/s]."""
        return self.mdot0 * np.sqrt(self.theta2) / self.delta2

    @property
    def N1_corrected(self) -> float:
        """Corrected LP speed N1 / sqrt(theta2), relative to its design value."""
        return self.N1 / np.sqrt(self.theta2)


def _flow_per_area(Pt, Tt, M, gas):
    """mdot / A = MFP(M) Pt / sqrt(Tt) [kg/(s m^2)]."""
    return mass_flow_parameter(M, gas) * Pt / np.sqrt(Tt)


@dataclass
class TurbofanEngine:
    """A turbofan sized at a design point, then flown anywhere.

    Build one with :meth:`design`; then :meth:`operate` (given Tt4) or :meth:`operate_at_thrust`.
    Both nozzles are convergent, as on most subsonic transport engines.
    """

    design_point: OperatingPoint
    components: Components
    cold: Gas
    hot: Gas
    h_PR: float
    include_fuel_mass: bool
    # frozen geometry and matching constants (from the design point)
    tau_tH: float
    booster_work_ratio: float
    C4: float  # mdot4 sqrt(Tt4) / Pt4 (choked HPT nozzle)
    A9: float  # core nozzle throat area [m^2]
    A19: float  # fan nozzle throat area [m^2]
    fan_work: float  # cpc (Tt13 - Tt2) at design [J/kg]
    hpc_work: float  # cpc (Tt3 - Tt25) at design [J/kg]

    # ------------------------------------------------------------------ construction
    @classmethod
    def design(
        cls,
        flight: FlightCondition,
        alpha: float,
        pi_f: float,
        pi_c: float,
        Tt4: float,
        pi_cL: float = 1.0,
        thrust: float | None = None,
        mdot0: float | None = None,
        components: Components = Components.modern(),  # noqa: B008 (frozen dataclass)
        cold: Gas = AIR,
        hot: Gas = COMBUSTION_GAS,
        h_PR: float = H_PR_JET_A,
        include_fuel_mass: bool = True,
    ) -> TurbofanEngine:
        """Size an engine at a design point, by its ``thrust`` [N] or inlet flow ``mdot0``."""
        if (thrust is None) == (mdot0 is None):
            raise ValueError("give exactly one of thrust or mdot0")
        kw = cls._cycle_kwargs(components, cold, hot, h_PR, include_fuel_mass)
        cyc = turbofan(flight, alpha, pi_f, pi_c, Tt4, pi_cL=pi_cL, **kw)
        F_spec = float(cyc.specific_thrust)
        if mdot0 is None:
            mdot0 = thrust / F_spec
        mdot_core = mdot0 / (1.0 + alpha)
        f = float(cyc.f)
        m = 1.0 + f if include_fuel_mass else 1.0
        st, ex = cyc.stations, cyc.extras
        Pt9 = float(st["5"].P) * components.pi_n
        Pt19 = float(st["13"].P) * components.pi_fn
        Tt5, Tt13 = float(st["5"].T), float(st["13"].T)
        A9 = mdot_core * m / _flow_per_area(Pt9, Tt5, float(ex["M9"]), hot)
        A19 = alpha * mdot_core / _flow_per_area(Pt19, Tt13, float(ex["M19"]), cold)
        C4 = mdot_core * m * np.sqrt(Tt4) / float(st["4"].P)
        Tt2, Tt25, Tt3 = float(st["2"].T), float(st["25"].T), float(st["3"].T)
        point = OperatingPoint(
            flight=flight,
            Tt4=Tt4,
            alpha=alpha,
            pi_f=pi_f,
            pi_cL=pi_cL,
            pi_cH=pi_c / (pi_f * pi_cL),
            mdot_core=mdot_core,
            thrust=mdot0 * F_spec,
            fuel_flow=mdot_core * f,
            N1=1.0,
            N2=1.0,
            cycle=cyc,
        )
        return cls(
            design_point=point,
            components=components,
            cold=cold,
            hot=hot,
            h_PR=h_PR,
            include_fuel_mass=include_fuel_mass,
            tau_tH=float(ex["tau_tH"]),
            booster_work_ratio=(Tt25 - Tt13) / (Tt13 - Tt2),
            C4=C4,
            A9=A9,
            A19=A19,
            fan_work=cold.cp * (Tt13 - Tt2),
            hpc_work=cold.cp * (Tt3 - Tt25),
        )

    @staticmethod
    def _cycle_kwargs(components, cold, hot, h_PR, include_fuel_mass):
        return {
            "components": components,
            "cold": cold,
            "hot": hot,
            "h_PR": h_PR,
            "core_nozzle": "convergent",
            "fan_nozzle": "convergent",
            "include_fuel_mass": include_fuel_mass,
        }

    # ------------------------------------------------------------------ matching
    def _cycle(self, flight, Tt4, x):
        pi_f, pi_cL, pi_cH, alpha = np.exp(x)
        kw = self._cycle_kwargs(
            self.components, self.cold, self.hot, self.h_PR, self.include_fuel_mass
        )
        return turbofan(flight, alpha, pi_f, pi_f * pi_cL * pi_cH, Tt4, pi_cL=pi_cL, **kw)

    def _flows(self, cyc, Tt4):
        """(core air flow, bypass flow allowed by the fan nozzle, core-nozzle capacity)."""
        st, ex = cyc.stations, cyc.extras
        f = float(cyc.f)
        m = 1.0 + f if self.include_fuel_mass else 1.0
        mdot_core = self.C4 * float(st["4"].P) / np.sqrt(Tt4) / m
        Pt19 = float(st["13"].P) * self.components.pi_fn
        bypass = self.A19 * _flow_per_area(Pt19, float(st["13"].T), float(ex["M19"]), self.cold)
        Pt9 = float(st["5"].P) * self.components.pi_n
        core_capacity = self.A9 * _flow_per_area(Pt9, float(st["5"].T), float(ex["M9"]), self.hot)
        return mdot_core, m, bypass, core_capacity

    def _residuals(self, x, flight, Tt4):
        cyc = self._cycle(flight, Tt4, x)
        st, ex = cyc.stations, cyc.extras
        alpha = np.exp(x[3])
        if not np.isfinite(float(cyc.V9)):
            return np.full(4, 1e3)
        mdot_core, m, bypass, core_capacity = self._flows(cyc, Tt4)
        Tt2, Tt13, Tt25 = (float(st[k].T) for k in ("2", "13", "25"))
        return np.array(
            [
                float(ex["tau_tH"]) / self.tau_tH - 1.0,
                (Tt25 - Tt13) / (Tt13 - Tt2) / self.booster_work_ratio - 1.0,
                np.log(alpha * mdot_core / bypass),
                np.log(mdot_core * m / core_capacity),
            ]
        )

    def _x0(self, guess: OperatingPoint | None):
        p = guess or self.design_point
        return np.log([p.pi_f, p.pi_cL, p.pi_cH, p.alpha])

    def _solve(self, x0, flight, Tt4):
        sol = root(self._residuals, x0, args=(flight, Tt4), method="hybr", options={"xtol": 1e-12})
        ok = bool(sol.success) and np.max(np.abs(self._residuals(sol.x, flight, Tt4))) < 1e-8
        return sol.x, ok

    def _march(self, start: OperatingPoint, flight: FlightCondition, Tt4: float):
        """Continuation: walk from a solved point to the target in steps, blending the flight
        condition (M0, T0, log P0) and Tt4, halving the step whenever a solve fails."""
        a, b = start.flight, flight
        x, s, ds = self._x0(start), 0.0, 0.25
        while s < 1.0:
            t = min(1.0, s + ds)
            fc = FlightCondition(
                M0=a.M0 + t * (b.M0 - a.M0),
                T0=a.T0 + t * (b.T0 - a.T0),
                P0=float(np.exp(np.log(a.P0) + t * (np.log(b.P0) - np.log(a.P0)))),
            )
            x_new, ok = self._solve(x, fc, start.Tt4 + t * (Tt4 - start.Tt4))
            if ok:
                x, s, ds = x_new, t, min(0.5, 2 * ds)
            else:
                ds /= 2
                if ds < 1e-4:
                    return x, False
        return x, True

    # ------------------------------------------------------------------ public API
    def operate(
        self, flight: FlightCondition, Tt4: float, guess: OperatingPoint | None = None
    ) -> OperatingPoint:
        """Solve the engine's operating point at ``flight`` and burner exit temperature ``Tt4``.

        Starts from ``guess`` (a nearby solved point) or the design point; if a direct solve
        fails it marches there by continuation. Check ``converged`` on the result.
        """
        start = guess or self.design_point
        x, ok = self._solve(self._x0(start), flight, Tt4)
        if not ok:
            x, ok = self._march(start, flight, Tt4)
        cyc = self._cycle(flight, Tt4, x)
        pi_f, pi_cL, pi_cH, alpha = np.exp(x)
        mdot_core, _, _, _ = self._flows(cyc, Tt4)
        st = cyc.stations
        fan_work = self.cold.cp * (float(st["13"].T) - float(st["2"].T))
        hpc_work = self.cold.cp * (float(st["3"].T) - float(st["25"].T))
        mdot0 = (1.0 + alpha) * mdot_core
        return OperatingPoint(
            flight=flight,
            Tt4=float(Tt4),
            alpha=float(alpha),
            pi_f=float(pi_f),
            pi_cL=float(pi_cL),
            pi_cH=float(pi_cH),
            mdot_core=float(mdot_core),
            thrust=float(mdot0 * cyc.specific_thrust),
            fuel_flow=float(mdot_core * cyc.f),
            N1=float(np.sqrt(fan_work / self.fan_work)),
            N2=float(np.sqrt(hpc_work / self.hpc_work)),
            cycle=cyc,
            converged=ok,
        )

    def operate_at_thrust(
        self,
        flight: FlightCondition,
        thrust: float,
        start: OperatingPoint | None = None,
        step: float = 0.03,
    ) -> OperatingPoint:
        """Find the burner exit temperature Tt4 (the throttle) that gives ``thrust`` [N].

        Walks Tt4 from ``start`` (default: the design Tt4 at this flight condition) in relative
        steps of ``step``, each solve seeded with the previous point, until the target is
        bracketed; then refines with Brent's method. Raises ``ValueError`` if the target lies
        outside the range where the model converges.
        """
        here = start or self.operate(flight, self.design_point.Tt4)
        if not here.converged:
            raise ValueError("no converged starting point at this flight condition")
        direction = -1.0 if here.thrust > thrust else 1.0
        cache = {here.Tt4: here}
        prev = here
        for _ in range(200):
            nxt = self.operate(flight, prev.Tt4 * (1.0 + direction * step), guess=prev)
            if not nxt.converged:
                raise ValueError(f"thrust {thrust:.0f} N is outside the converged range")
            cache[nxt.Tt4] = nxt
            if (nxt.thrust - thrust) * (prev.thrust - thrust) <= 0:
                break
            prev = nxt
        else:
            raise ValueError("could not bracket the target thrust")

        def excess(Tt4):
            near = cache[min(cache, key=lambda t: abs(t - Tt4))]
            p = self.operate(flight, Tt4, guess=near)
            cache[Tt4] = p
            return p.thrust - thrust

        lo, hi = sorted((prev.Tt4, nxt.Tt4))
        Tt4 = brentq(excess, lo, hi, xtol=1e-9, rtol=1e-12)
        return self.operate(flight, Tt4, guess=cache[min(cache, key=lambda t: abs(t - Tt4))])
