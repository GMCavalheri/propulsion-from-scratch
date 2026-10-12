"""Component performance parameters for non-ideal cycle analysis."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Components:
    """Figures of merit of each component (Mattingly, *Elements of Propulsion*, Ch. 4 and 7).

    The defaults describe *ideal* components, so ``Components()`` reproduces the ideal cycle.

    pi_d_max  inlet total-pressure ratio before ram-recovery losses (pi_d = pi_d_max * eta_r)
    inlet_shock_losses  apply the MIL-E-5007 ram recovery eta_r(M0) in supersonic flight
    e_c, e_f  polytropic efficiency of the compressor(s) and of the fan
    e_t       polytropic efficiency of the turbine(s)
    pi_b      burner total-pressure ratio;  eta_b  burner (combustion) efficiency
    eta_m     mechanical efficiency of each spool (shaft power delivered / turbine power)
    pi_n      core nozzle total-pressure ratio;  pi_fn  fan (bypass) nozzle total-pressure ratio
    """

    pi_d_max: float = 1.0
    inlet_shock_losses: bool = False
    e_c: float = 1.0
    e_f: float = 1.0
    e_t: float = 1.0
    pi_b: float = 1.0
    eta_b: float = 1.0
    eta_m: float = 1.0
    pi_n: float = 1.0
    pi_fn: float = 1.0

    @classmethod
    def modern(cls) -> Components:
        """Representative values for a modern subsonic turbofan.

        These are **assumptions**, chosen inside the ranges Mattingly (2006, Table 4.4) gives for
        current technology; they are not data for any particular engine.
        """
        return cls(
            pi_d_max=0.995,
            inlet_shock_losses=True,
            e_c=0.90,
            e_f=0.89,
            e_t=0.89,
            pi_b=0.96,
            eta_b=0.995,
            eta_m=0.99,
            pi_n=0.99,
            pi_fn=0.99,
        )

    def with_(self, **changes) -> Components:
        """Copy with some parameters changed, e.g. ``Components.modern().with_(e_c=0.92)``."""
        return replace(self, **changes)
