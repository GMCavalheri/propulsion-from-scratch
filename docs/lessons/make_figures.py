"""Teaching figures for the lesson series (docs/figures/lessons/).

Run with ``uv run python docs/lessons/make_figures.py``. Validation figures live in
``validation/``; these illustrate ideas.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from propulsion import plotting as P
from propulsion.atmosphere import isa
from propulsion.brayton_cycle import ideal_turbojet, optimum_compressor_pressure_ratio, ts_diagram
from propulsion.component_models import (
    Components,
    compressor_isentropic_efficiency,
    turbine_isentropic_efficiency,
    turbojet,
)
from propulsion.flight import FlightCondition
from propulsion.gas import (
    AIR,
    COMBUSTION_GAS,
    area_ratio,
    mass_flow_parameter,
    stagnation_pressure_ratio,
)
from propulsion.units import FT

CRUISE = FlightCondition.at_altitude(11000.0, 0.8, geopotential=True)

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


def _annotate_stations(ax, labels, x, y, dx=0.0, dy=0.0):
    for k, xi, yi in zip(labels, x, y, strict=True):
        ax.plot(xi, yi, "o", color=P.REFERENCE, ms=4)
        ax.annotate(k, (xi, yi), xytext=(4 + dx, 4 + dy), textcoords="offset points", fontsize=9)


def l2_ts_pv():
    perf = ideal_turbojet(CRUISE, 20.0, 1600.0)
    labels, T, s, Tp, sp = ts_diagram(perf)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
    ax = axes[0]
    ax.plot(sp, Tp, color=P.SERIES[0])
    _annotate_stations(ax, labels[:1] + labels[2:], np.delete(s, 1), np.delete(T, 1))
    _annotate_stations(ax, ["2"], s[1:2], T[1:2], dx=10, dy=4)
    ax.set_xlabel("entropy s − s₀ [J/(kg·K)]")
    ax.set_ylabel("temperature [K]")
    ax.set_title("T–s: ideal turbojet, πc = 20, Tt4 = 1600 K")
    ax.text(150, 1150, "heat in\n(constant P)", fontsize=8, color=P.TEXT_MUTED)
    ax.text(620, 250, "heat out to the\natmosphere (P₀)", fontsize=8, color=P.TEXT_MUTED)

    # P-v: isentropes P v^g = const, isobars for heat addition and rejection
    g, R = AIR.gamma, AIR.R
    st = perf.stations
    T0, P0 = float(st["0"].T), float(st["0"].P)
    T3, P3, T4 = float(st["3"].T), float(st["3"].P), float(st["4"].T)
    T9 = float(st["9"].T)
    Tc = np.geomspace(T0, T3, 50)
    Pc = P0 * (Tc / T0) ** (g / (g - 1))
    Th = np.geomspace(T4, T9, 50)
    Ph = P3 * (Th / T4) ** (g / (g - 1))
    segs = [
        (Tc, Pc),
        (np.geomspace(T3, T4, 50), np.full(50, P3)),
        (Th, Ph),
        (np.geomspace(T9, T0, 50), np.full(50, P0)),
    ]
    ax = axes[1]
    for Tseg, Pseg in segs:
        ax.plot(R * Tseg / Pseg, Pseg / 1e3, color=P.SERIES[1])
    pts = {"0": (T0, P0), "3": (T3, P3), "4": (T4, P3), "9": (T9, P0)}
    _annotate_stations(
        ax, list(pts), [R * t / p for t, p in pts.values()], [p / 1e3 for _, p in pts.values()]
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    for axis in (ax.xaxis, ax.yaxis):
        axis.set_major_formatter(mticker.FormatStrFormatter("%g"))
        axis.set_minor_formatter(mticker.NullFormatter())
    ax.set_xticks([0.1, 0.2, 0.5, 1, 2, 5])
    ax.set_yticks([20, 50, 100, 200, 500])
    ax.set_xlabel("specific volume v [m³/kg]")
    ax.set_ylabel("pressure [kPa]")
    ax.set_title("P–v (log–log axes)")
    return save(fig, "l2_ts_pv.png")


def l2_pressure_ratio_sweep():
    pi_c = np.geomspace(1.0, 60.0, 300)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.0))
    for i, Tt4 in enumerate((1200.0, 1400.0, 1600.0, 1800.0)):
        p = ideal_turbojet(CRUISE, pi_c, Tt4)
        c = P.SERIES[i]
        axes[0].plot(pi_c, p.specific_thrust, color=c, label=f"Tt4 = {Tt4:.0f} K")
        axes[1].plot(pi_c, p.tsfc * 1e6, color=c)
        opt = optimum_compressor_pressure_ratio(CRUISE, Tt4)
        po = ideal_turbojet(CRUISE, opt, Tt4)
        axes[0].plot(opt, po.specific_thrust, "o", color=c, ms=5)
    axes[0].set_xscale("log")
    axes[0].set_xlabel("compressor pressure ratio πc")
    axes[0].set_ylabel("specific thrust F/ṁ₀ [N·s/kg]")
    axes[0].set_title("Specific thrust (● = optimum)")
    axes[0].legend()
    axes[1].set_xscale("log")
    axes[1].set_ylim(20, 50)
    axes[1].set_xlabel("compressor pressure ratio πc")
    axes[1].set_ylabel("TSFC [mg/(N·s)]")
    axes[1].set_title("Fuel consumption")
    p = ideal_turbojet(CRUISE, pi_c, 1600.0)
    axes[2].plot(pi_c, p.eta_thermal, label="thermal ηT")
    axes[2].plot(pi_c, p.eta_propulsive, label="propulsive ηP")
    axes[2].plot(pi_c, p.eta_overall, label="overall ηO", color=P.REFERENCE)
    axes[2].set_xscale("log")
    axes[2].set_ylim(0, 1)
    axes[2].set_xlabel("compressor pressure ratio πc")
    axes[2].set_title("Efficiencies, Tt4 = 1600 K")
    axes[2].legend()
    fig.suptitle("Ideal turbojet at 11 km, Mach 0.8", x=0.02, ha="left", weight="bold", y=1.02)
    return save(fig, "l2_pressure_ratio_sweep.png")


def l2_mach_sweep():
    fig, ax = plt.subplots(figsize=(6.5, 4.0))
    M0 = np.linspace(0.0, 4.0, 400)
    for i, pi_c in enumerate((1.0, 4.0, 12.0, 24.0)):
        F = [
            float(
                ideal_turbojet(
                    FlightCondition.at_altitude(11000.0, m, geopotential=True), pi_c, 1800.0
                ).specific_thrust
            )
            for m in M0
        ]
        label = "πc = 1 (ramjet)" if pi_c == 1.0 else f"πc = {pi_c:.0f}"
        ax.plot(M0, F, color=P.SERIES[i], label=label)
    ax.set_xlabel("flight Mach number M₀")
    ax.set_ylabel("specific thrust F/ṁ₀ [N·s/kg]")
    ax.set_title("Ideal turbojet, Tt4 = 1800 K, 11 km")
    ax.set_ylim(0, None)
    ax.legend()
    return save(fig, "l2_mach_sweep.png")


def l3_polytropic():
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.0))
    pi = np.geomspace(1.01, 50.0, 300)
    for i, e in enumerate((0.85, 0.90, 0.95)):
        c = P.SERIES[i]
        axes[0].plot(
            pi, compressor_isentropic_efficiency(pi, AIR.gamma, e), color=c, label=f"e = {e:.2f}"
        )
        axes[0].axhline(e, color=c, lw=0.8, ls=":")
        tau_t = np.linspace(0.4, 0.999, 300)
        pi_t = tau_t ** (COMBUSTION_GAS.gamma / ((COMBUSTION_GAS.gamma - 1) * e))
        axes[1].plot(
            1 / pi_t,
            turbine_isentropic_efficiency(tau_t, COMBUSTION_GAS.gamma, e),
            color=c,
            label=f"e = {e:.2f}",
        )
        axes[1].axhline(e, color=c, lw=0.8, ls=":")
    axes[0].set_xscale("log")
    axes[0].set_xlabel("compressor pressure ratio πc")
    axes[0].set_ylabel("isentropic efficiency")
    axes[0].set_title("Compressor: η falls below e")
    axes[0].legend(loc="lower left")
    axes[1].set_xscale("log")
    axes[1].set_xlabel("turbine expansion ratio 1/πt")
    axes[1].set_title("Turbine: η rises above e (reheat)")
    axes[1].legend(loc="lower right")
    for ax in axes:
        ax.set_ylim(0.7, 1.0)
        ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%g"))
    return save(fig, "l3_polytropic.png")


def l3_loss_steps():
    """Remove the idealisations one at a time (cruise, pi_c = 20, Tt4 = 1600 K)."""
    m = Components.modern()
    steps = [
        ("ideal\n(Lesson 2)", {"components": Components(), "hot": AIR, "include_fuel_mass": False})
    ]
    steps.append(("hot-gas\nproperties", {"components": Components(), "include_fuel_mass": False}))
    c = Components()
    steps.append(("fuel\nmass", {"components": c}))
    for name, change in [
        ("inlet\nπd", {"pi_d_max": m.pi_d_max}),
        ("compressor\ne_c", {"e_c": m.e_c}),
        ("burner\nπb, ηb", {"pi_b": m.pi_b, "eta_b": m.eta_b}),
        ("turbine\ne_t", {"e_t": m.e_t}),
        ("shaft\nηm", {"eta_m": m.eta_m}),
        ("nozzle\nπn", {"pi_n": m.pi_n}),
    ]:
        c = c.with_(**change)
        steps.append((name, {"components": c}))
    perfs = [turbojet(CRUISE, 20.0, 1600.0, **kw) for _, kw in steps]
    labels = [n for n, _ in steps]
    x = np.arange(len(steps))
    fig, axes = plt.subplots(2, 1, figsize=(10, 6.2), sharex=True)
    for ax, values, unit, color in [
        (axes[0], [float(p.tsfc) * 1e6 for p in perfs], "TSFC [mg/(N·s)]", P.SERIES[1]),
        (axes[1], [float(p.specific_thrust) for p in perfs], "F/ṁ₀ [N·s/kg]", P.SERIES[0]),
    ]:
        ax.plot(x, values, color=color, marker="o", lw=1.2)
        ax.plot(x[:1], values[:1], "o", color=P.REFERENCE)
        for xi, v in zip(x, values, strict=True):
            ax.annotate(
                f"{v:.1f}",
                (xi, v),
                xytext=(0, 7),
                textcoords="offset points",
                ha="center",
                fontsize=8,
            )
        ax.margins(y=0.2)
        ax.set_ylabel(unit)
        ax.grid(axis="x", visible=False)
    axes[1].set_xticks(x, labels, fontsize=8)
    axes[0].set_title(
        "Removing the idealisations one at a time (11 km, M 0.8, πc = 20, Tt4 = 1600 K)"
    )
    return save(fig, "l3_loss_steps.png")


def l3_ts_ideal_vs_real():
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    kw = {"hot": AIR, "include_fuel_mass": False}
    for perf, label, color in [
        (turbojet(CRUISE, 20.0, 1600.0, Components(), **kw), "ideal components", P.REFERENCE),
        (
            turbojet(CRUISE, 20.0, 1600.0, Components.modern(), **kw),
            "modern components",
            P.SERIES[1],
        ),
    ]:
        labels, T, s, Tp, sp = ts_diagram(perf)
        ax.plot(
            sp,
            Tp,
            color=color,
            label=label,
            lw=1.6 if color == P.REFERENCE else 2.0,
            ls="--" if color == P.REFERENCE else "-",
        )
        if color != P.REFERENCE:
            _annotate_stations(ax, labels[2:], s[2:], T[2:])
    ax.set_xlabel("entropy s − s₀ [J/(kg·K)]")
    ax.set_ylabel("temperature [K]")
    ax.set_title("Losses tilt compression and expansion to the right")
    ax.legend(loc="upper left")
    return save(fig, "l3_ts_ideal_vs_real.png")


def l3_pressure_ratio_sweep():
    pi_c = np.geomspace(2.0, 400.0, 600)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.0))
    for i, Tt4 in enumerate((1400.0, 1600.0, 1800.0)):
        c = P.SERIES[i]
        ideal = turbojet(CRUISE, pi_c, Tt4, Components())
        real = turbojet(CRUISE, pi_c, Tt4, Components.modern())
        axes[0].plot(pi_c, ideal.specific_thrust, color=c, ls="--", lw=1.2)
        axes[0].plot(pi_c, real.specific_thrust, color=c, label=f"Tt4 = {Tt4:.0f} K")
        axes[1].plot(pi_c, ideal.tsfc * 1e6, color=c, ls="--", lw=1.2)
        axes[1].plot(pi_c, real.tsfc * 1e6, color=c)
        j = np.nanargmin(real.tsfc)
        axes[1].plot(pi_c[j], real.tsfc[j] * 1e6, "o", color=c, ms=5)
    for ax in axes:
        ax.set_xscale("log")
        ax.set_xlabel("compressor pressure ratio πc")
        ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%g"))
    axes[0].set_ylabel("specific thrust F/ṁ₀ [N·s/kg]")
    axes[0].set_ylim(0, None)
    axes[0].set_title("Specific thrust (dashed: ideal components)")
    axes[0].legend()
    axes[1].set_ylabel("TSFC [mg/(N·s)]")
    axes[1].set_ylim(20, 50)
    axes[1].set_title("TSFC (● = minimum with losses)")
    return save(fig, "l3_pressure_ratio_sweep.png")


FIGURES = [
    l1_atmosphere,
    l1_compressible_flow,
    l2_ts_pv,
    l2_pressure_ratio_sweep,
    l2_mach_sweep,
    l3_polytropic,
    l3_loss_steps,
    l3_ts_ideal_vs_real,
    l3_pressure_ratio_sweep,
]

if __name__ == "__main__":
    P.use_style()
    for make in FIGURES:
        print(make())
