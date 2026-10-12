"""The ideal (closed) Brayton cycle: isentropic compression and expansion, heat added and
rejected at constant pressure, one calorically perfect gas.

With compressor temperature ratio tau = pi^((g-1)/g) and cycle temperature ratio
tau_lambda = T3 / T1 (turbine inlet over compressor inlet):

    eta_th = 1 - 1/tau                                   (depends on pressure ratio only)
    w_net / (cp T1) = tau_lambda (1 - 1/tau) - (tau - 1)  (turbine work - compressor work)
    w_net is maximum at tau* = sqrt(tau_lambda), where T2 = T4.

Reference: Mattingly, *Elements of Propulsion*, 2nd ed., Ch. 2 and 5.
"""

from __future__ import annotations

import numpy as np


def brayton_thermal_efficiency(pi, gamma: float = 1.4):
    """eta_th = 1 - pi^(-(g-1)/g) for pressure ratio ``pi``."""
    return 1.0 - np.asarray(pi, dtype=float) ** (-(gamma - 1.0) / gamma)


def brayton_specific_work(pi, tau_lambda, gamma: float = 1.4):
    """Net work per unit mass divided by cp T1."""
    tau = np.asarray(pi, dtype=float) ** ((gamma - 1.0) / gamma)
    return tau_lambda * (1.0 - 1.0 / tau) - (tau - 1.0)


def brayton_optimum_tau(tau_lambda):
    """Compressor temperature ratio that maximises net work: sqrt(tau_lambda)."""
    return np.sqrt(tau_lambda)
