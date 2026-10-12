"""Containers shared by every cycle model: station states and engine performance."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..gas import Gas, entropy_change


@dataclass(frozen=True)
class Station:
    """Gas state at an engine station. ``T``/``P`` are stagnation values except at the free
    stream (``"0"``) and nozzle exits (``"9"``, ``"19"``), where the static state is stored."""

    T: np.ndarray
    P: np.ndarray
    gas: Gas
    static: bool = False

    def entropy(self, ref: Station):
        """Entropy relative to ``ref`` [J/(kg K)], using this station's gas for cp and R."""
        return entropy_change(self.gas, ref.T, ref.P, self.T, self.P)


@dataclass(frozen=True)
class CyclePerformance:
    """Uninstalled performance per unit of engine inlet air flow.

    ``specific_thrust`` is F / mdot0 [N s/kg = m/s]; ``tsfc`` is fuel flow per unit thrust
    [kg/(N s)]; ``f`` is the fuel/air ratio of the core. Efficiencies follow Mattingly's
    definitions: thermal = power to the jets / fuel power, propulsive = thrust power / power to
    the jets, overall = thrust power / fuel power. "Power to the jets" is the kinetic-energy gain
    with every jet *fully expanded* to ambient pressure, so that an under-expanded (convergent)
    nozzle's pressure thrust is not counted as free energy and eta_p stays below 1.
    """

    specific_thrust: np.ndarray
    tsfc: np.ndarray
    f: np.ndarray
    eta_thermal: np.ndarray
    eta_propulsive: np.ndarray
    eta_overall: np.ndarray
    V0: np.ndarray
    V9: np.ndarray
    stations: dict[str, Station] = field(default_factory=dict)
    extras: dict[str, np.ndarray] = field(default_factory=dict)


def ts_diagram(perf: CyclePerformance, order=("0", "2", "3", "4", "5", "9"), points: int = 40):
    """Temperature and entropy along the cycle, for a T-s plot of a scalar design point.

    Entropy is accumulated process by process, each step using the gas of its downstream
    station (cold gas up to station 3, hot gas from the burner on), and is relative to the
    free stream. Compression and expansion are drawn as straight segments between stations;
    heat addition (3 -> 4) follows the burner's pressure path, and the open-cycle heat
    rejection is drawn along the ambient isobar through station 0. For a single-gas cycle that
    isobar passes exactly through the nozzle exit; with two gases it can miss it slightly,
    because the two gas models do not share an entropy datum.

    Returns ``(labels, T_stations, s_stations, T_path, s_path)``.
    """
    st = perf.stations
    labels = [k for k in order if k in st]
    T = np.array([float(st[k].T) for k in labels])
    Pk = np.array([float(st[k].P) for k in labels])
    s = np.zeros(len(labels))
    for i in range(1, len(labels)):
        gas = st[labels[i]].gas
        s[i] = s[i - 1] + float(entropy_change(gas, T[i - 1], Pk[i - 1], T[i], Pk[i]))

    T_path, s_path = [], []
    for i, (a, b) in enumerate(zip(labels[:-1], labels[1:], strict=True)):
        if (a, b) == ("3", "4"):
            Tp = np.geomspace(T[i], T[i + 1], points)
            frac = np.log(Tp / T[i]) / np.log(T[i + 1] / T[i])
            Pp = Pk[i] * (Pk[i + 1] / Pk[i]) ** frac
            sp = s[i] + entropy_change(st[b].gas, T[i], Pk[i], Tp, Pp)
        else:
            Tp = np.linspace(T[i], T[i + 1], points)
            sp = np.linspace(s[i], s[i + 1], points)
        T_path.append(Tp)
        s_path.append(sp)
    # heat rejection to the atmosphere along the ambient isobar through station 0
    ref = st[labels[0]]
    Tp = np.geomspace(T[-1], T[0], points)
    T_path.append(Tp)
    s_path.append(entropy_change(ref.gas, ref.T, ref.P, Tp, ref.P))
    return labels, T, s, np.concatenate(T_path), np.concatenate(s_path)
