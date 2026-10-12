"""Teaching figures for the lesson series (docs/figures/lessons/).

Run with ``uv run python docs/lessons/make_figures.py``. Validation figures live in
``validation/``; these illustrate ideas.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from propulsion import plotting as P
from propulsion.atmosphere import isa
from propulsion.gas import AIR, area_ratio, mass_flow_parameter, stagnation_pressure_ratio
from propulsion.units import FT

OUT = P.FIGURES / "lessons"


def save(fig, name):
    return P.save(fig, name, OUT)


def l1_atmosphere():
    z = np.linspace(0.0, 20000.0, 401)
    a = isa(z)
    fig, axes = plt.subplots(1, 3, figsize=(10, 4.2), sharey=True)
    km = z / 1e3
    axes[0].plot(a.T, km, color=P.SERIES[0])
    axes[0].set_xlabel("temperature T [K]")
    axes[0].set_ylabel("geometric altitude [km]")
    axes[1].plot(a.delta, km, color=P.SERIES[1], label="pressure  δ = P/P_SL")
    axes[1].plot(a.sigma, km, color=P.SERIES[2], label="density  σ = ρ/ρ_SL")
    axes[1].set_xlabel("ratio to sea level")
    axes[1].legend(loc="upper right")
    axes[2].plot(a.a, km, color=P.SERIES[3])
    axes[2].set_xlabel("speed of sound a [m/s]")
    cruise = 35000 * FT / 1e3
    for ax in axes:
        ax.axhline(11.0, color=P.TEXT_MUTED, lw=0.8, ls=":")
        ax.axhline(cruise, color=P.REFERENCE, lw=0.8, ls="--")
    axes[0].text(217, 11.3, "tropopause (11 km)", fontsize=8, color=P.TEXT_MUTED)
    axes[0].text(250, cruise - 0.9, "FL350 cruise", fontsize=8)
    fig.suptitle("The International Standard Atmosphere", x=0.02, ha="left", weight="bold")
    return save(fig, "l1_isa.png")


def l1_compressible_flow():
    M = np.linspace(0.01, 2.5, 500)
    g = AIR.gamma
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    ax = axes[0]
    ax.plot(M, 1 + 0.5 * (g - 1) * M**2, label="Tt / T")
    ax.plot(M, stagnation_pressure_ratio(M, g), label="Pt / P")
    ax.plot(M, area_ratio(M, g), label="A / A*")
    ax.set_ylim(0, 6)
    ax.set_xlabel("Mach number M")
    ax.set_title("Isentropic ratios (γ = 1.4)")
    ax.legend()
    ax = axes[1]
    mfp = mass_flow_parameter(M, AIR)
    ax.plot(M, mfp * 1e3, color=P.SERIES[4])
    ax.axvline(1.0, color=P.REFERENCE, lw=0.8, ls="--")
    ax.annotate(
        "choked: flow per unit area\nis at its maximum",
        xy=(1.0, mfp.max() * 1e3),
        xytext=(1.1, 22.0),
        arrowprops={"arrowstyle": "->", "color": P.TEXT_MUTED},
        fontsize=9,
    )
    ax.set_xlabel("Mach number M")
    ax.set_ylabel("MFP = ṁ√Tt / (Pt A)  [g·√K / (N·s)]")
    ax.set_title("Mass-flow parameter")
    return save(fig, "l1_flow_relations.png")


FIGURES = [l1_atmosphere, l1_compressible_flow]

if __name__ == "__main__":
    P.use_style()
    for make in FIGURES:
        print(make())
