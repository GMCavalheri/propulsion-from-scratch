"""Two-spool separate-exhaust turbofan (Phase 3)."""

from .ideal import ideal_jet_velocities, optimum_bypass_ratio, optimum_fan_pressure_ratio
from .turbofan import turbofan

__all__ = [
    "ideal_jet_velocities",
    "optimum_bypass_ratio",
    "optimum_fan_pressure_ratio",
    "turbofan",
]
