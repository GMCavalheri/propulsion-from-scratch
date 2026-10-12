"""Off-design model vs published CFM56-7B26/3 and LEAP-1B28 data (Phase 4b).

Run with ``uv run python validation/engine_validation.py``. Writes
``docs/figures/engine_lto.png``, ``docs/figures/engine_throttle.png``,
``docs/figures/engine_lapse.png`` and ``validation/results/engine_validation.md``.

See ``engines.py`` for what is data, what is assumed and what is calibrated.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from propulsion import plotting as P  # noqa: E402
from propulsion.flight import FlightCondition  # noqa: E402
from propulsion.units import FT, tsfc_to_lb_per_lbf_h  # noqa: E402

from engines import ENGINE_COMPONENTS, ENGINES, PI_CL, SLS, calibrated_engine  # noqa: E402
from reference import LTO_MODES, icao, tcds  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"
FL350 = FlightCondition.at_altitude(35000 * FT, 0.78, geopotential=True)
COLORS = dict(zip(ENGINES, P.SERIES[:2], strict=True))


def throttle_line(engine, flight, Tt4_lo_frac=0.42, n=40):
    """Operating points from the design Tt4 down to a fraction of it (continuation)."""
    Tt4 = np.linspace(engine.design_point.Tt4, Tt4_lo_frac * engine.design_point.Tt4, n)
    pts, guess = [], None
    for t in Tt4:
        p = engine.operate(flight, t, guess=guess)
        if not p.converged:
            break
        pts.append(p)
        guess = p
    return pts


def lto_table():
    rows = {}
    for name in ENGINES:
        e, d = calibrated_engine(name), icao(name)
        for mode, frac in LTO_MODES:
            p = (
                e.design_point
                if frac == 1.0
                else e.operate_at_thrust(SLS, frac * d["rated_thrust"])
            )
            rows[name, mode] = (p, d["ff_" + mode])
    return rows


def figure_lto(rows):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    modes = [m for m, _ in LTO_MODES]
    x = np.arange(len(modes))
    for k, name in enumerate(ENGINES):
        c = COLORS[name]
        model = [rows[name, m][0].fuel_flow for m in modes]
        ref = [rows[name, m][1] for m in modes]
        dx = (k - 0.5) * 0.22
        axes[0].plot(
            x + dx,
            ref,
            "s",
            color=P.REFERENCE,
            ms=6,
            mfc="none",
            label="ICAO databank" if k == 0 else None,
        )
        axes[0].plot(x + dx, model, "o", color=c, label=f"model, {name}")
        err = 100 * (np.array(model) / np.array(ref) - 1)
        axes[1].plot(x, err, "o-", color=c, label=name)
        for xi, ei in zip(x, err, strict=True):
            axes[1].annotate(
                f"{ei:+.1f} %",
                (xi, ei),
                xytext=(8, -14 if k == 0 else 6),
                textcoords="offset points",
                fontsize=8,
                color=c,
            )
    labels = [f"{m}\n{int(100 * f)} %" for m, f in LTO_MODES]
    axes[0].set_xticks(x, labels)
    axes[0].set_ylabel("fuel flow [kg/s]")
    axes[0].set_title("ICAO LTO fuel flow, sea-level static ISA")
    axes[0].legend()
    axes[1].axhline(0, color=P.REFERENCE, lw=0.8)
    axes[1].set_xticks(x, labels)
    axes[1].set_ylabel("model − ICAO [% of ICAO]")
    axes[1].set_ylim(-28, 8)
    axes[1].set_title("Error (take-off is the calibration point)")
    axes[1].legend(loc="lower left")
    return P.save(fig, "engine_lto.png")


def figure_throttle(lines, rows):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    for name in ENGINES:
        c, pts = COLORS[name], lines[name]
        F = np.array([p.thrust for p in pts]) / 1e3
        axes[0].plot(F, [p.fuel_flow for p in pts], color=c, label=f"model, {name}")
        refF = [rows[name, m][0].thrust / 1e3 for m, _ in LTO_MODES]
        axes[0].plot(
            refF,
            [rows[name, m][1] for m, _ in LTO_MODES],
            "s",
            color=c,
            mfc="none",
            label=f"ICAO, {name}",
        )
        axes[1].plot(F, [100 * p.N1 for p in pts], color=c, label=f"N1, {name}")
        axes[1].plot(F, [100 * p.N2 for p in pts], color=c, ls="--", label=f"N2, {name}")
        axes[2].plot(F, [p.Tt45 - 273.15 for p in pts], color=c, label=f"Tt45, {name}")
        axes[2].plot(F, [p.Tt5 - 273.15 for p in pts], color=c, ls="--", label=f"Tt5, {name}")
        lim = tcds(name)
        axes[2].axhline(lim["egt_limit_takeoff_C"], color=c, lw=0.8, ls=":")
        axes[2].text(
            2,
            lim["egt_limit_takeoff_C"] + 8,
            f"TCDS EGT limit at {lim['egt_station']}",
            fontsize=7,
            color=c,
        )
    axes[0].set_xlabel("thrust [kN]")
    axes[0].set_ylabel("fuel flow [kg/s]")
    axes[0].set_title("Throttle line, sea-level static")
    axes[0].legend(fontsize=7)
    axes[1].set_xlabel("thrust [kN]")
    axes[1].set_ylabel("spool speed [% of rated]")
    axes[1].set_title("Spool speeds (N2 dashed)")
    axes[1].legend(fontsize=7)
    axes[2].set_xlabel("thrust [kN]")
    axes[2].set_ylabel("temperature [°C]")
    axes[2].set_title("LPT inlet / exit temperature")
    axes[2].legend(fontsize=7, loc="center right")
    return P.save(fig, "engine_throttle.png")


def figure_lapse(cruise_lines):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for name in ENGINES:
        e, c = calibrated_engine(name), COLORS[name]
        Tt4 = e.design_point.Tt4
        alt = np.linspace(0.0, 11000.0, 23)
        guess, F = None, []
        for h in alt:
            p = e.operate(
                FlightCondition.at_altitude(h, 0.78 * h / 11000.0 + 0.2), Tt4, guess=guess
            )
            F.append(p.thrust / e.design_point.thrust)
            guess = p
        axes[0].plot(alt / 1e3, F, color=c, label=name)
        pts = cruise_lines[name]
        axes[1].plot(
            [p.thrust / 1e3 for p in pts], [p.tsfc * 1e6 for p in pts], color=c, label=name
        )
    alt = np.linspace(0.0, 11000.0, 23)
    from propulsion.atmosphere import isa

    axes[0].plot(
        alt / 1e3, isa(alt).delta, color=P.REFERENCE, ls="--", lw=1.2, label="δ₀ = P₀/P_SL"
    )
    axes[0].set_xlabel("altitude [km] (Mach rising linearly 0.2 → 0.78)")
    axes[0].set_ylabel("thrust / rated thrust")
    axes[0].set_title("Thrust lapse along a climb, take-off Tt4 held")
    axes[0].legend()
    axes[1].set_xlabel("thrust [kN]")
    axes[1].set_ylabel("TSFC [mg/(N·s)]")
    axes[1].set_title("Cruise TSFC vs thrust, FL350 Mach 0.78")
    axes[1].set_ylim(14, 24)
    axes[1].legend()
    return P.save(fig, "engine_lapse.png")


def hot_day(name):
    """Rated thrust on an ISA+15 day: the throttle and turbine temperatures it needs."""
    e, d = calibrated_engine(name), icao(name)
    hot = FlightCondition.sea_level_static(dT=15.0)
    same_Tt4 = e.operate(hot, e.design_point.Tt4)
    rated = e.operate_at_thrust(hot, d["rated_thrust"], start=same_Tt4)
    return same_Tt4, rated


def write_results(rows, cruise_lines, hot):
    lines = [
        "# Engine validation: CFM56-7B26/3 and LEAP-1B28",
        "",
        "Generated by `validation/engine_validation.py`. Data: ICAO Engine Emissions Databank",
        "Issue 32 and EASA TCDS E.004 Issue 07 / E.115 Issue 09 (`validation/reference_data`).",
        f"Assumptions: polytropic efficiencies e_f = {ENGINE_COMPONENTS.e_f}, "
        f"e_c = {ENGINE_COMPONENTS.e_c}, e_t = {ENGINE_COMPONENTS.e_t}; booster ratio {PI_CL};",
        "no cooling or bleed flows; convergent nozzles. Take-off fuel flow is the calibration",
        "point (it fixes Tt4); every other number is a prediction.",
        "",
        "## Calibrated design points (sea-level static ISA, rated thrust)",
        "",
        "| Engine | BPR | OPR | rated thrust [kN] | fan PR (chosen) | Tt4 (calibrated) [K] "
        "| airflow [kg/s] | TSFC [mg/(N·s)] |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name in ENGINES:
        d, p = icao(name), calibrated_engine(name).design_point
        lines.append(
            f"| {name} | {d['bpr']:.2f} | {d['opr']:.2f} | {p.thrust / 1e3:.1f} | {p.pi_f:.3f} | "
            f"{p.Tt4:.1f} | {p.mdot0:.1f} | {p.tsfc * 1e6:.3f} |"
        )
    lines += [
        "",
        "## ICAO LTO fuel flow",
        "",
        "| Engine | mode | thrust [kN] | ICAO [kg/s] | model [kg/s] | error | Tt4 [K] "
        "| N1 [%] | N2 [%] | Tt45 [°C] |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name in ENGINES:
        for mode, _ in LTO_MODES:
            p, ref = rows[name, mode]
            err = 100 * (p.fuel_flow / ref - 1)
            note = " (calibrated)" if mode == "takeoff" else ""
            lines.append(
                f"| {name} | {mode} | {p.thrust / 1e3:.1f} | {ref:.4f} | {p.fuel_flow:.4f} | "
                f"{err:+.1f} %{note} | {p.Tt4:.0f} | {100 * p.N1:.1f} | {100 * p.N2:.1f} | "
                f"{p.Tt45 - 273.15:.0f} |"
            )
    lines += [
        "",
        "## Cruise (FL350, Mach 0.78, ISA): minimum TSFC along the throttle line",
        "",
        "| Engine | min TSFC [mg/(N·s)] | [lb/(lbf·h)] | at thrust [kN] |",
        "|---|---|---|---|",
    ]
    best = {}
    for name in ENGINES:
        pts = cruise_lines[name]
        p = min(pts, key=lambda q: q.tsfc)
        best[name] = p.tsfc
        lines.append(
            f"| {name} | {p.tsfc * 1e6:.2f} | {tsfc_to_lb_per_lbf_h(p.tsfc):.3f} | "
            f"{p.thrust / 1e3:.1f} |"
        )
    gain = 100 * (1 - best[ENGINES[1]] / best[ENGINES[0]])
    lines += [
        "",
        f"Model: LEAP-1B28 minimum cruise TSFC is {gain:.1f} % below the CFM56-7B26/3's.",
        "",
        "## Hot day (ISA+15, sea-level static)",
        "",
        "| Engine | thrust at the ISA Tt4 [% rated] | Tt4 for rated thrust [K] | "
        "Tt45 rise [K] | TCDS EGT limit [°C] (station) | model Tt45 [°C] |",
        "|---|---|---|---|---|---|",
    ]
    for name in ENGINES:
        same, rated = hot[name]
        dp, lim = calibrated_engine(name).design_point, tcds(name)
        lines.append(
            f"| {name} | {100 * same.thrust / dp.thrust:.1f} | {rated.Tt4:.0f} | "
            f"{rated.Tt45 - dp.Tt45:+.0f} | {lim['egt_limit_takeoff_C']:.0f} "
            f"({lim['egt_station']}) | {rated.Tt45 - 273.15:.0f} |"
        )
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "engine_validation.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    P.use_style()
    rows = lto_table()
    sls_lines = {n: throttle_line(calibrated_engine(n), SLS, 0.4) for n in ENGINES}
    cruise_lines = {n: throttle_line(calibrated_engine(n), FL350, 0.62) for n in ENGINES}
    hot = {n: hot_day(n) for n in ENGINES}
    print(figure_lto(rows))
    print(figure_throttle(sls_lines, rows))
    print(figure_lapse(cruise_lines))
    write_results(rows, cruise_lines, hot)


if __name__ == "__main__":
    main()
