"""Compressor and turbine: polytropic and isentropic efficiency.

The polytropic (small-stage) efficiency e is the efficiency of an infinitesimal compression
or expansion step. It is the same for every stage of a well-designed machine, so it is the
natural parameter for comparing machines of different pressure ratio (Mattingly 2006,
Ch. 6; Saravanamuttoo et al., *Gas Turbine Theory*, Ch. 2). Integrating dT/T =
(g-1)/(g e) dP/P for a compressor and dT/T = e (g-1)/g dP/P for a turbine gives

    compressor:  tau_c = pi_c^((g-1)/(g e_c)),   eta_c = (pi_c^((g-1)/g) - 1) / (tau_c - 1)
    turbine:     pi_t = tau_t^(g/((g-1) e_t)),   eta_t = (1 - tau_t) / (1 - tau_t^(1/e_t))
"""

from __future__ import annotations

import numpy as np


def compressor_tau(pi_c, gamma: float, e_c: float):
    """Total-temperature ratio of a compressor of pressure ratio ``pi_c``."""
    return np.asarray(pi_c, dtype=float) ** ((gamma - 1.0) / (gamma * e_c))


def compressor_pi(tau_c, gamma: float, e_c: float):
    """Pressure ratio of a compressor of total-temperature ratio ``tau_c`` (inverse)."""
    return np.asarray(tau_c, dtype=float) ** (gamma * e_c / (gamma - 1.0))


def compressor_isentropic_efficiency(pi_c, gamma: float, e_c: float):
    """Isentropic efficiency eta_c = ideal work / actual work."""
    pi_c = np.asarray(pi_c, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        eta = (pi_c ** ((gamma - 1.0) / gamma) - 1.0) / (compressor_tau(pi_c, gamma, e_c) - 1.0)
    return np.where(pi_c == 1.0, e_c, eta)[()]


def turbine_pi(tau_t, gamma: float, e_t: float):
    """Pressure ratio of a turbine of total-temperature ratio ``tau_t`` (< 1)."""
    return np.asarray(tau_t, dtype=float) ** (gamma / ((gamma - 1.0) * e_t))


def turbine_tau(pi_t, gamma: float, e_t: float):
    """Total-temperature ratio of a turbine of pressure ratio ``pi_t`` (inverse)."""
    return np.asarray(pi_t, dtype=float) ** ((gamma - 1.0) * e_t / gamma)


def turbine_isentropic_efficiency(tau_t, gamma: float, e_t: float):
    """Isentropic efficiency eta_t = actual work / ideal work."""
    tau_t = np.asarray(tau_t, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        eta = (1.0 - tau_t) / (1.0 - tau_t ** (1.0 / e_t))
    return np.where(tau_t == 1.0, e_t, eta)[()]
