"""Phase 5 trade studies: why modern engines favour high bypass ratio (and what it costs).

Run with ``uv run python validation/trade_studies.py``. Writes ``docs/figures/trade_bpr_opr.png``,
``docs/figures/trade_carpet.png``, ``docs/figures/trade_size_noise.png`` and
``validation/results/trade_studies.md``.

All cycles use the component assumptions of ``engines.ENGINE_COMPONENTS`` and a booster ratio of
1.6; every point gets its own best fan pressure ratio. The CFM56-7B26/3 and LEAP-1B28 markers are
the cruise operating points of the calibrated off-design models (Phase 4).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from propulsion import plotting as P  # noqa: E402
from propulsion.flight import FlightCondition  # noqa: E402
from propulsion.trade_studies import fan_diameter, jet_noise_index, sweep  # noqa: E402
from propulsion.turbofan_model import turbofan  # noqa: E402
from propulsion.units import FT, tsfc_to_lb_per_lbf_h  # noqa: E402

from engines import ENGINE_COMPONENTS, ENGINES, PI_CL, SLS, calibrated_engine  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"
FL350 = FlightCondition.at_altitude(35000 * FT, 0.78, geopotential=True)
KW = {"components": ENGINE_COMPONENTS, "core_nozzle": "convergent", "fan_nozzle": "convergent"}
SWEEP = {**KW, "pi_f_max": 10.0}
ALPHA = np.linspace(1.0, 14.0, 27)


def cruise_bucket(name):
    """The calibrated engine's minimum-TSFC operating point at FL350, Mach 0.78."""
    e = calibrated_engine(name)
    pts, guess = [], None
    for t in np.linspace(1.0, 0.62, 77) * e.design_point.Tt4:
        guess = e.operate(FL350, t, guess=guess)
        pts.append(guess)
    return min((p for p in pts if p.converged), key=lambda p: p.tsfc)


def figure_bpr_opr(buckets):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    Tt4 = 1300.0
    for i, opr in enumerate((25.0, 30.0, 40.0, 50.0)):
        s = sweep(FL350, ALPHA, opr, Tt4, pi_cL=PI_CL, **SWEEP)
        axes[0].plot(ALPHA, s.tsfc[:, 0, 0] * 1e6, color=P.SERIES[i], label=f"OPR {opr:.0f}")
        axes[1].plot(ALPHA, s.pi_f[:, 0, 0], color=P.SERIES[i], label=f"OPR {opr:.0f}")
    for name, marker in zip(ENGINES, ("s", "D"), strict=True):
        b = buckets[name]
        axes[0].plot(b.alpha, b.tsfc * 1e6, marker, color=P.REFERENCE, ms=7, mfc="none")
        axes[0].annotate(
            f"{name}\n(OPR {b.pi_c:.0f}, Tt4 {b.Tt4:.0f} K)",
            (b.alpha, b.tsfc * 1e6),
            xytext=(8, 6),
            textcoords="offset points",
            fontsize=8,
        )
        axes[1].plot(b.alpha, b.pi_f, marker, color=P.REFERENCE, ms=7, mfc="none")
    axes[0].set_xlabel("bypass ratio α")
    axes[0].set_ylabel("TSFC [mg/(N·s)]")
    axes[0].set_title(f"Cruise TSFC, best fan, Tt4 = {Tt4:.0f} K")
    axes[0].set_ylim(14, 26)
    axes[0].legend(loc="upper right")
    axes[1].set_xlabel("bypass ratio α")
    axes[1].set_ylabel("best fan pressure ratio πf")
    axes[1].set_title("High bypass needs a low-pressure-ratio fan")
    axes[1].legend()
    fig.suptitle(
        "FL350, Mach 0.78 (markers: calibrated engine models at their cruise bucket)",
        x=0.02,
        ha="left",
        weight="bold",
        y=1.02,
    )
    return P.save(fig, "trade_bpr_opr.png")


def figure_carpet():
    alpha = np.array([3.0, 5.0, 7.0, 9.0, 11.0, 13.0])
    Tt4 = np.array([1150.0, 1250.0, 1350.0, 1450.0, 1550.0])
    s = sweep(FL350, alpha, 40.0, Tt4, pi_cL=PI_CL, **SWEEP)
    F, S = s.specific_thrust[:, 0, :], s.tsfc[:, 0, :] * 1e6
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for j, t in enumerate(Tt4):
        ax.plot(F[:, j], S[:, j], color=P.SERIES[1], lw=1.4)
        ax.annotate(
            f"Tt4 {t:.0f} K",
            (F[0, j], S[0, j]),
            xytext=(6, -6),
            textcoords="offset points",
            fontsize=8,
            color=P.SERIES[1],
        )
    for i, a in enumerate(alpha):
        ax.plot(F[i, :], S[i, :], color=P.SERIES[0], lw=1.4)
        ax.annotate(
            f"α = {a:.0f}",
            (F[i, 0], S[i, 0]),
            xytext=(-8, 4),
            textcoords="offset points",
            fontsize=8,
            color=P.SERIES[0],
            ha="right",
        )
    ax.set_xlabel("specific thrust F/ṁ₀ [N·s/kg]")
    ax.set_ylabel("TSFC [mg/(N·s)]")
    ax.set_title("Carpet plot, FL350 Mach 0.78, OPR 40\n(blue: constant α, orange: constant Tt4)")
    ax.set_xlim(20, 380)
    return P.save(fig, "trade_carpet.png")


def size_noise_table():
    """Take-off: engines of the same thrust, OPR and Tt4 but different bypass ratio."""
    thrust, opr, Tt4 = 120e3, 35.0, 1450.0
    alpha = np.array([1.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.0])
    s = sweep(SLS, alpha, opr, Tt4, pi_cL=PI_CL, **SWEEP)
    rows = []
    for k, a in enumerate(alpha):
        pf = s.pi_f[k, 0, 0]
        p = turbofan(SLS, a, pf, opr, Tt4, pi_cL=PI_CL, **KW)
        mdot = thrust / float(p.specific_thrust)
        cruise = sweep(FL350, a, opr, 1300.0, pi_cL=PI_CL, **SWEEP).tsfc[0, 0, 0]
        rows.append(
            (
                a,
                pf,
                mdot,
                float(fan_diameter(mdot, SLS)),
                float(jet_noise_index(p, thrust)),
                float(p.tsfc),
                cruise,
            )
        )
    return rows, (thrust, opr, Tt4)


def figure_size_noise(rows):
    a, _, _, D, noise, _, cruise = (np.array(c) for c in zip(*rows, strict=True))
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.0))
    axes[0].plot(a, cruise * 1e6, "o-", color=P.SERIES[2])
    axes[0].set_ylabel("cruise TSFC [mg/(N·s)]")
    axes[0].set_title("The gain: fuel")
    axes[1].plot(a, D, "o-", color=P.SERIES[1])
    axes[1].set_ylabel("fan diameter [m]")
    axes[1].set_title("The price: size (and weight, drag)")
    axes[2].plot(a, noise - noise[0], "o-", color=P.SERIES[0])
    axes[2].set_ylabel("jet noise index, relative to α = 1 [dB]")
    axes[2].set_title("A bonus: quieter jets")
    for ax in axes:
        ax.set_xlabel("bypass ratio α")
    fig.suptitle(
        "Same 120 kN take-off thrust, OPR 35: what bypass ratio buys and costs",
        x=0.02,
        ha="left",
        weight="bold",
        y=1.03,
    )
    return P.save(fig, "trade_size_noise.png")


def leap_vs_cfm(buckets):
    """Walk the CFM56 cruise cycle to the LEAP's, one design change at a time."""
    c, l = buckets[ENGINES[0]], buckets[ENGINES[1]]
    steps = [
        ("CFM56-7B26/3 cruise cycle", c.alpha, c.pi_f, c.pi_c, c.pi_cL, c.Tt4),
        ("+ LEAP overall pressure ratio", c.alpha, c.pi_f, l.pi_c, c.pi_cL, c.Tt4),
        ("+ LEAP turbine temperature", c.alpha, c.pi_f, l.pi_c, c.pi_cL, l.Tt4),
        (
            "+ LEAP fan (bypass ratio and fan pressure ratio)",
            l.alpha,
            l.pi_f,
            l.pi_c,
            l.pi_cL,
            l.Tt4,
        ),
    ]
    out = []
    for label, a, pf, pc, pcl, t in steps:
        p = turbofan(FL350, a, pf, pc, t, pi_cL=pcl, **KW)
        out.append(
            (label, a, pf, pc, t, float(p.tsfc), float(p.eta_thermal), float(p.eta_propulsive))
        )
    return out


def write_results(buckets, walk, rows, setup):
    thrust, opr, Tt4 = setup
    lines = [
        "# Trade studies",
        "",
        "Generated by `validation/trade_studies.py`. Components as `engines.ENGINE_COMPONENTS`,",
        f"booster ratio {PI_CL}, convergent nozzles, best fan pressure ratio at every point.",
        "",
        "## From CFM56-7B to LEAP-1B at cruise (FL350, Mach 0.78), one change at a time",
        "",
        "| step | α | πf | OPR | Tt4 [K] | TSFC [mg/(N·s)] | change | ηT | ηP |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    prev = None
    for label, a, pf, pc, t, s, et, ep in walk:
        change = "" if prev is None else f"{100 * (s / prev - 1):+.1f} %"
        lines.append(
            f"| {label} | {a:.2f} | {pf:.3f} | {pc:.1f} | {t:.0f} | {s * 1e6:.2f} | {change} | "
            f"{et:.3f} | {ep:.3f} |"
        )
        prev = s
    total = 100 * (walk[-1][5] / walk[0][5] - 1)
    lines += [
        "",
        f"Total: {total:+.1f} % TSFC. The order matters (a bigger fan needs the hotter core to",
        "drive it), so the split between steps is indicative; the total is not.",
        "",
        f"## Same take-off thrust ({thrust / 1e3:.0f} kN), OPR {opr:.0f}, Tt4 {Tt4:.0f} K",
        "",
        "Fan-face Mach 0.6 and hub/tip ratio 0.3 assumed for the diameter; the jet-noise index is",
        "Lighthill's eighth-power scaling (relative values only). Cruise TSFC at Tt4 1300 K.",
        "",
        "| α | best πf | airflow [kg/s] | fan diameter [m] | jet noise index [dB, rel.] | "
        "take-off TSFC [mg/(N·s)] | cruise TSFC [mg/(N·s)] |",
        "|---|---|---|---|---|---|---|",
    ]
    n0 = rows[0][4]
    for a, pf, mdot, D, noise, s_to, s_cr in rows:
        lines.append(
            f"| {a:.0f} | {pf:.3f} | {mdot:.0f} | {D:.2f} | {noise - n0:+.1f} | {s_to * 1e6:.2f} | "
            f"{s_cr * 1e6:.2f} |"
        )
    lines += [
        "",
        "## Calibrated engine models at their cruise bucket",
        "",
        "| engine | α | πf | OPR | Tt4 [K] | thrust [kN] | TSFC [mg/(N·s)] | [lb/(lbf·h)] |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name in ENGINES:
        b = buckets[name]
        lines.append(
            f"| {name} | {b.alpha:.2f} | {b.pi_f:.3f} | {b.pi_c:.1f} | {b.Tt4:.0f} | "
            f"{b.thrust / 1e3:.1f} | {b.tsfc * 1e6:.2f} | {tsfc_to_lb_per_lbf_h(b.tsfc):.3f} |"
        )
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "trade_studies.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    P.use_style()
    buckets = {n: cruise_bucket(n) for n in ENGINES}
    print(figure_bpr_opr(buckets))
    print(figure_carpet())
    rows, setup = size_noise_table()
    print(figure_size_noise(rows))
    write_results(buckets, leap_vs_cfm(buckets), rows, setup)


if __name__ == "__main__":
    main()
