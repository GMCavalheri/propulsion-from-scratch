"""Verification scorecard for Phases 1-4 and the cycle figures.

Run with ``uv run python validation/cycle_validation.py``. Writes
``validation/results/cycle_validation.md``, ``docs/figures/engine_ts.png`` and
``docs/figures/engine_map.png``.

Every check compares against an exact identity, a closed form or a published table (cited
inline); the same checks run, with tolerances, in ``tests/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from propulsion import plotting as P  # noqa: E402
from propulsion.atmosphere import isa  # noqa: E402
from propulsion.brayton_cycle import (  # noqa: E402
    ideal_turbojet,
    optimum_compressor_pressure_ratio,
    ts_diagram,
)
from propulsion.component_models import Components, turbojet  # noqa: E402
from propulsion.flight import FlightCondition  # noqa: E402
from propulsion.gas import AIR, H_PR_JET_A  # noqa: E402
from propulsion.off_design_performance import TurbofanEngine  # noqa: E402
from propulsion.turbofan_model import (  # noqa: E402
    optimum_bypass_ratio,
    optimum_fan_pressure_ratio,
    turbofan,
)
from propulsion.units import FT  # noqa: E402

from engines import ENGINES, SLS, calibrated_engine  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"
FL350 = FlightCondition.at_altitude(35000 * FT, 0.78, geopotential=True)
CRUISE = FlightCondition.at_altitude(11000.0, 0.8, geopotential=True)
IDEAL = {"components": Components(), "hot": AIR, "include_fuel_mass": False}

# US Standard Atmosphere 1976 (NOAA-S/T 76-1562): Table 4 base values (geopotential) and
# Table I at 10 km geometric
ISA_TABLE = [
    ("H = 11 km (geopotential)", 11000.0, True, 216.65, 22632.06, None),
    ("H = 20 km (geopotential)", 20000.0, True, 216.65, 5474.889, None),
    ("H = 32 km (geopotential)", 32000.0, True, 228.65, 868.0187, None),
    ("Z = 10 km (geometric)", 10000.0, False, 223.252, 2.6500e4, 0.41351),
]


def rel(a, b):
    return abs(float(a) / float(b) - 1.0)


def isa_rows():
    rows = []
    for label, h, geo, T, Pref, rho in ISA_TABLE:
        a = isa(h, geopotential=geo)
        err = max(rel(a.T, T), rel(a.P, Pref), rel(a.rho, rho) if rho else 0.0)
        rows.append(
            ("Atmosphere", f"ISA vs US 1976 table, {label}", f"{err:.1e}", "≤ printed digits")
        )
    return rows


def ideal_cycle_rows():
    worst_energy, worst_opt = 0.0, 0.0
    for fc in (SLS, CRUISE, FlightCondition(2.0, 216.65, 19.4e3)):
        for pi_c in (4.0, 12.0, 30.0):
            p = ideal_turbojet(fc, pi_c, 1600.0)
            ke = 0.5 * (p.V9**2 - p.V0**2)
            worst_energy = max(worst_energy, rel(ke / (p.f * H_PR_JET_A), p.eta_thermal))
        grid = np.geomspace(1.0, 80.0, 400001)
        best = grid[np.nanargmax(ideal_turbojet(fc, grid, 1700.0).specific_thrust)]
        worst_opt = max(worst_opt, rel(best, optimum_compressor_pressure_ratio(fc, 1700.0)))
    real = turbojet(CRUISE, 20.0, 1600.0, **IDEAL)
    ideal = ideal_turbojet(CRUISE, 20.0, 1600.0)
    limit = max(rel(real.specific_thrust, ideal.specific_thrust), rel(real.tsfc, ideal.tsfc))
    return [
        (
            "Ideal turbojet",
            "η_T = KE gain / fuel energy = 1 − 1/(τr τc), 9 cases",
            f"{worst_energy:.1e}",
            "exact identity",
        ),
        (
            "Ideal turbojet",
            "brute-force optimum πc vs √τλ/τr, 3 flight conditions",
            f"{worst_opt:.1e}",
            "grid step 1e-5",
        ),
        (
            "Real turbojet",
            "ideal components reproduce the ideal turbojet",
            f"{limit:.1e}",
            "exact limit",
        ),
    ]


def turbofan_rows():
    alpha = np.linspace(0.0, 20.0, 200001)
    p = turbofan(CRUISE, alpha, 1.7, 30.0, 1600.0, **IDEAL)
    a_best = alpha[np.nanargmin(p.tsfc)]
    a_err = abs(a_best - optimum_bypass_ratio(CRUISE, 1.7, 30.0, 1600.0))
    pf = np.linspace(1.05, 3.0, 200001)
    q = turbofan(CRUISE, 8.0, pf, 35.0, 1600.0, **IDEAL)
    pf_err = abs(pf[np.nanargmin(q.tsfc)] - optimum_fan_pressure_ratio(CRUISE, 8.0, 35.0, 1600.0))
    m = Components.modern().with_(e_f=Components.modern().e_c)
    zero = turbofan(CRUISE, 0.0, 1.6, 25.0, 1600.0, pi_cL=1.8, components=m)
    jet = turbojet(CRUISE, 25.0, 1600.0, components=m)
    return [
        (
            "Turbofan",
            "α = 0 reproduces the turbojet (modern components)",
            f"{rel(zero.tsfc, jet.tsfc):.1e}",
            "exact limit",
        ),
        (
            "Turbofan",
            "brute-force optimum bypass ratio vs closed form α*",
            f"{a_err:.1e} (abs.)",
            "grid step 1e-4",
        ),
        (
            "Turbofan",
            "brute-force optimum fan pressure ratio vs closed form πf*",
            f"{pf_err:.1e} (abs.)",
            "grid step 1e-5",
        ),
    ]


def off_design_rows():
    design = {"alpha": 5.1, "pi_f": 1.65, "pi_c": 32.8, "Tt4": 1650.0, "pi_cL": 1.6}
    e = TurbofanEngine.design(SLS, thrust=117e3, **design)
    p = e.operate(SLS, design["Tt4"])
    repro = max(
        rel(p.thrust, e.design_point.thrust),
        rel(p.alpha, e.design_point.alpha),
        rel(p.fuel_flow, e.design_point.fuel_flow),
    )
    s = TurbofanEngine.design(SLS, thrust=117e3, include_fuel_mass=False, **design)
    a, b = FlightCondition.at_altitude(3000.0, 0.5), FlightCondition.at_altitude(9000.0, 0.5)
    pa, pb = s.operate(a, 1300.0), s.operate(b, 1300.0 * b.T0 / a.T0)
    sim = max(
        rel(pa.thrust / a.P0, pb.thrust / b.P0),
        rel(pa.N1_corrected, pb.N1_corrected),
        rel(pa.corrected_flow, pb.corrected_flow),
    )
    return [
        (
            "Off-design",
            "operate() at the design point reproduces the design",
            f"{repro:.1e}",
            "exact",
        ),
        (
            "Off-design",
            "corrected similarity, 3 km vs 9 km at equal M0 and Tt4/T0",
            f"{sim:.1e}",
            "exact (fuel mass off)",
        ),
    ]


def figure_ts():
    fig, ax = plt.subplots(figsize=(7.5, 5))
    order = ("0", "2", "13", "25", "3", "4", "45", "5", "9")
    for name, c in zip(ENGINES, P.SERIES[:2], strict=True):
        labels, T, s, Tp, sp = ts_diagram(
            calibrated_engine(name).design_point.cycle, order=order, points=40
        )
        n = len(Tp) - 40  # the last 40 points close the cycle along the ambient isobar
        ax.plot(sp[:n], Tp[:n], color=c, label=name)
        ax.plot(sp[n - 1 :], Tp[n - 1 :], color=c, ls="--", lw=1.0)
        for k, x, y in zip(labels, s, T, strict=True):
            if k in ("3", "4", "45", "5"):
                ax.plot(x, y, "o", color=c, ms=4)
                ax.annotate(
                    k, (x, y), xytext=(4, 4), textcoords="offset points", fontsize=8, color=c
                )
    ax.set_xlabel("entropy s − s₀ [J/(kg·K)]")
    ax.set_ylabel("temperature [K]")
    ax.set_title("Core T–s at take-off, sea-level static ISA (calibrated models)")
    ax.text(
        400,
        300,
        "dashed: heat rejection to the atmosphere\n(the step at 9 is the two-gas "
        "model:\ncold and hot gas have no common entropy datum)",
        fontsize=8,
        color=P.TEXT_MUTED,
    )
    ax.legend()
    return P.save(fig, "engine_ts.png")


def figure_map(name="LEAP-1B28"):
    """Thrust and TSFC at the take-off Tt4 over the flight envelope (off-design map)."""
    e = calibrated_engine(name)
    alt = np.linspace(0.0, 12000.0, 13)
    mach = np.linspace(0.0, 0.85, 10)
    F = np.full((alt.size, mach.size), np.nan)
    S = np.full_like(F, np.nan)
    for j, m in enumerate(mach):
        guess = None
        for i, h in enumerate(alt):
            p = e.operate(FlightCondition.at_altitude(h, m), e.design_point.Tt4, guess=guess)
            if p.converged:
                F[i, j], S[i, j], guess = p.thrust / 1e3, p.tsfc * 1e6, p
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax, Z, title, cmap in [
        (axes[0], F, "Thrust [kN]", "Blues"),
        (axes[1], S, "TSFC [mg/(N·s)]", "Oranges"),
    ]:
        cs = ax.contourf(mach, alt / 1e3, Z, levels=12, cmap=cmap)
        ax.contour(mach, alt / 1e3, Z, levels=12, colors="k", linewidths=0.4)
        fig.colorbar(cs, ax=ax)
        ax.set_xlabel("flight Mach number")
        ax.set_ylabel("altitude [km]")
        ax.set_title(title)
        ax.grid(False)
    fig.suptitle(
        f"{name} model at its take-off Tt4 ({e.design_point.Tt4:.0f} K), ISA",
        x=0.02,
        ha="left",
        weight="bold",
        y=1.02,
    )
    return P.save(fig, "engine_map.png")


def main():
    P.use_style()
    rows = isa_rows() + ideal_cycle_rows() + turbofan_rows() + off_design_rows()
    lines = [
        "# Cycle verification scorecard",
        "",
        "Generated by `validation/cycle_validation.py`. Relative errors unless marked.",
        "",
        "| Module | Check | Error | Reference |",
        "|---|---|---|---|",
        *[f"| {m} | {c} | {e} | {r} |" for m, c, e, r in rows],
    ]
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "cycle_validation.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(figure_ts())
    print(figure_map())


if __name__ == "__main__":
    main()
