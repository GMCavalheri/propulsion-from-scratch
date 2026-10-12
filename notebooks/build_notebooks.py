"""Generate and execute the demo notebooks from the cell sources below.

Run with ``uv run python notebooks/build_notebooks.py``. Keeping the sources here (instead of
hand-editing .ipynb JSON) makes the notebooks reviewable in diffs and reproducible: rebuilds are
byte-identical.
"""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient

HERE = Path(__file__).resolve().parent

SETUP = """\
import sys
import numpy as np
import matplotlib.pyplot as plt
from propulsion import plotting as P
from propulsion.flight import FlightCondition
from propulsion.units import FT, tsfc_to_lb_per_lbf_h

P.use_style()
np.set_printoptions(precision=4, suppress=True)
FL350 = FlightCondition.at_altitude(35000 * FT, 0.78, geopotential=True)
SLS = FlightCondition.sea_level_static()"""

VALIDATION = """
sys.path.insert(0, "../validation")  # calibrated engine models and cited data
from engines import calibrated_engine, ENGINES
from reference import icao, tcds, LTO_MODES"""

NOTEBOOKS: dict[str, list[tuple[str, str]]] = {
    "01_atmosphere_and_gas.ipynb": [
        (
            "md",
            """\
# 1 · The air an engine breathes

The International Standard Atmosphere, stagnation properties, the mass-flow parameter and
corrected flow. Lesson: [01](../docs/lessons/01-atmosphere-and-compressible-flow.md) ·
Theory: [atmosphere and gas](../docs/atmosphere_and_gas.md).""",
        ),
        (
            "code",
            SETUP
            + """
from propulsion.atmosphere import isa, pressure_altitude
from propulsion.gas import AIR, COMBUSTION_GAS, mass_flow_parameter, stagnation_pressure_ratio""",
        ),
        ("md", "## The standard atmosphere at a few altitudes"),
        (
            "code",
            """\
for z in [0.0, 5000.0, 11000.0, 15000.0, 20000.0]:
    a = isa(z)
    print(f"z = {z/1e3:5.1f} km   T = {float(a.T):7.2f} K   P = {float(a.P):9.1f} Pa   "
          f"rho = {float(a.rho):.4f} kg/m3   a = {float(a.a):6.1f} m/s")""",
        ),
        (
            "md",
            """\
## Cruise at FL350, Mach 0.78

Flight levels are pressure altitudes, so the ISA is evaluated at 35,000 ft *geopotential*.""",
        ),
        (
            "code",
            """\
print(f"T0 = {FL350.T0:.2f} K, P0 = {FL350.P0:.0f} Pa, V0 = {float(FL350.V0()):.1f} m/s")
print(f"ram: tau_r = {float(FL350.tau_r()):.4f}, pi_r = {float(FL350.pi_r()):.4f}")
print(f"fan face: Tt0 = {float(FL350.Tt0()):.1f} K, Pt0 = {float(FL350.Pt0()):.0f} Pa")
print(f"pressure altitude of 30 kPa: {pressure_altitude(30e3, geopotential=True)/FT:.0f} ft")""",
        ),
        (
            "md",
            """\
## Mass-flow parameter and corrected flow

A 1.6 m² fan face at Mach 0.6 passes very different *physical* flows at sea level and at
cruise, but the same *corrected* flow.""",
        ),
        (
            "code",
            """\
mfp = float(mass_flow_parameter(0.6, AIR))
for name, fc in [("sea-level static", SLS), ("FL350, M 0.78", FL350)]:
    Tt, Pt = float(fc.Tt0()), float(fc.Pt0())
    mdot = mfp * Pt * 1.6 / np.sqrt(Tt)
    corrected = mdot * np.sqrt(Tt / 288.15) / (Pt / 101325.0)
    print(f"{name:17s} mdot = {mdot:6.1f} kg/s   corrected = {corrected:6.1f} kg/s")
M = np.linspace(0.05, 2.5, 300)
fig, ax = plt.subplots(figsize=(6, 3.5))
ax.plot(M, mass_flow_parameter(M, AIR) * 1e3, label="cold air")
ax.plot(M, mass_flow_parameter(M, COMBUSTION_GAS) * 1e3, label="hot gas")
ax.set_xlabel("Mach number"); ax.set_ylabel("MFP [g·√K/(N·s)]"); ax.legend()
plt.show()""",
        ),
    ],
    "02_ideal_brayton_cycle.ipynb": [
        (
            "md",
            """\
# 2 · The ideal Brayton cycle and the turbojet

Lesson: [02](../docs/lessons/02-ideal-brayton-cycle.md) ·
Theory: [ideal Brayton cycle](../docs/brayton_cycle.md).""",
        ),
        (
            "code",
            SETUP
            + """
from propulsion.brayton_cycle import (ideal_turbojet, optimum_compressor_pressure_ratio,
                                      ts_diagram, brayton_thermal_efficiency)
CRUISE = FlightCondition.at_altitude(11000.0, 0.8, geopotential=True)""",
        ),
        ("md", "## The worked example of Lesson 2"),
        (
            "code",
            """\
p = ideal_turbojet(CRUISE, pi_c=20.0, Tt4=1600.0)
print(f"F/m0 = {float(p.specific_thrust):.1f} N s/kg,  f = {float(p.f):.5f},  "
      f"TSFC = {float(p.tsfc)*1e6:.2f} mg/(N s) = {tsfc_to_lb_per_lbf_h(float(p.tsfc)):.3f} lb/(lbf h)")
print(f"eta_T = {float(p.eta_thermal):.3f}, eta_P = {float(p.eta_propulsive):.3f}, "
      f"eta_O = {float(p.eta_overall):.3f}")
print(f"optimum pi_c = {float(optimum_compressor_pressure_ratio(CRUISE, 1600.0)):.2f}")
labels, T, s, Tp, sp = ts_diagram(p)
fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(sp, Tp)
for k, x, y in zip(labels, s, T):
    ax.annotate(k, (x, y), xytext=(4, 4), textcoords="offset points")
ax.set_xlabel("s - s0 [J/(kg K)]"); ax.set_ylabel("T [K]")
plt.show()""",
        ),
        (
            "md",
            """\
## Sweeps

Everything broadcasts: one call evaluates a whole grid of pressure ratios and temperatures.""",
        ),
        (
            "code",
            """\
pi_c = np.geomspace(1.0, 60.0, 200)
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
for Tt4 in (1200.0, 1600.0, 2000.0):
    q = ideal_turbojet(CRUISE, pi_c, Tt4)
    axes[0].plot(pi_c, q.specific_thrust, label=f"Tt4 = {Tt4:.0f} K")
    axes[1].plot(pi_c, q.tsfc * 1e6)
for ax in axes:
    ax.set_xscale("log"); ax.set_xlabel("pi_c")
axes[0].set_ylabel("F/m0 [N s/kg]"); axes[1].set_ylabel("TSFC [mg/(N s)]"); axes[1].set_ylim(15, 50)
axes[0].legend(); plt.show()""",
        ),
        ("md", "## Fast flight needs less compression: the ramjet limit"),
        (
            "code",
            """\
for M0 in (0.0, 0.8, 2.0, 3.0):
    fc = FlightCondition.at_altitude(11000.0, M0, geopotential=True)
    print(f"M0 = {M0:3.1f}: optimum pi_c = {float(optimum_compressor_pressure_ratio(fc, 1600.0)):7.2f}")
print("closed Brayton efficiency at pi = 30:", round(float(brayton_thermal_efficiency(30.0)), 4))""",
        ),
    ],
    "03_component_models.ipynb": [
        (
            "md",
            """\
# 3 · Real components

Polytropic efficiency, the burner with two gases, nozzles, and the loss bill.
Lesson: [03](../docs/lessons/03-real-components.md) ·
Theory: [component models](../docs/component_models.md).""",
        ),
        (
            "code",
            SETUP
            + """
from propulsion.component_models import (Components, turbojet, fuel_air_ratio,
                                         compressor_isentropic_efficiency)
from propulsion.gas import AIR, COMBUSTION_GAS, H_PR_JET_A
CRUISE = FlightCondition.at_altitude(11000.0, 0.8, geopotential=True)""",
        ),
        ("md", "## Polytropic vs isentropic efficiency"),
        (
            "code",
            """\
for pi in (2.0, 10.0, 30.0, 50.0):
    print(f"pi_c = {pi:4.0f}: eta_c = {float(compressor_isentropic_efficiency(pi, 1.4, 0.90)):.4f}"
          "  (e_c = 0.90)")""",
        ),
        (
            "md",
            """\
## The burner datum

Enthalpies are measured from the heating-value reference temperature (298.15 K). The textbook
form (each gas from 0 K) over-counts the heat when the gases differ.""",
        ),
        (
            "code",
            """\
f = fuel_air_ratio(700.0, 1600.0, AIR, COMBUSTION_GAS, H_PR_JET_A, 0.995)
f0 = fuel_air_ratio(700.0, 1600.0, AIR, COMBUSTION_GAS, H_PR_JET_A, 0.995, T_ref=0.0)
print(f"f (datum 298.15 K) = {float(f):.5f};  f (each gas from 0 K) = {float(f0):.5f}  "
      f"(+{100*(float(f0)/float(f)-1):.1f} %)")""",
        ),
        ("md", "## Removing the idealisations one at a time"),
        (
            "code",
            """\
m = Components.modern()
steps = [("ideal (Lesson 2)", dict(components=Components(), hot=AIR, include_fuel_mass=False)),
         ("+ hot gas", dict(components=Components(), include_fuel_mass=False)),
         ("+ fuel mass", dict(components=Components()))]
c = Components()
for name, change in [("+ inlet", dict(pi_d_max=m.pi_d_max)), ("+ compressor", dict(e_c=m.e_c)),
                     ("+ burner", dict(pi_b=m.pi_b, eta_b=m.eta_b)), ("+ turbine", dict(e_t=m.e_t)),
                     ("+ shaft", dict(eta_m=m.eta_m)), ("+ nozzle", dict(pi_n=m.pi_n))]:
    c = c.with_(**change)
    steps.append((name, dict(components=c)))
for name, kw in steps:
    p = turbojet(CRUISE, 20.0, 1600.0, **kw)
    print(f"{name:18s} F/m0 = {float(p.specific_thrust):7.1f}   TSFC = {float(p.tsfc)*1e6:6.2f} mg/(N s)")""",
        ),
        ("md", "## Convergent vs fully expanded nozzle"),
        (
            "code",
            """\
for kind in ("ideal", "convergent"):
    p = turbojet(CRUISE, 20.0, 1600.0, m, nozzle=kind)
    print(f"{kind:10s} F/m0 = {float(p.specific_thrust):6.1f}  M9 = {float(p.extras['M9']):.2f}  "
          f"P9/P0 = {float(p.extras['P9'])/CRUISE.P0:.2f}  eta_P = {float(p.eta_propulsive):.3f}")""",
        ),
    ],
    "04_turbofan.ipynb": [
        (
            "md",
            """\
# 4 · The turbofan

Lesson: [04](../docs/lessons/04-turbofan.md) · Theory: [turbofan model](../docs/turbofan_model.md).""",
        ),
        (
            "code",
            SETUP
            + """
from propulsion.component_models import Components
from propulsion.gas import AIR
from propulsion.turbofan_model import (turbofan, optimum_bypass_ratio,
                                       optimum_fan_pressure_ratio)""",
        ),
        ("md", "## The worked example of Lesson 4"),
        (
            "code",
            """\
p = turbofan(FL350, alpha=5.5, pi_f=1.7, pi_c=32.0, Tt4=1450.0, pi_cL=1.6,
             components=Components.modern())
e = p.extras
print(f"F/m0 = {float(p.specific_thrust):.1f} N s/kg (core {float(e['specific_thrust_core']):.1f}, "
      f"fan {float(e['specific_thrust_fan']):.1f})")
print(f"TSFC = {float(p.tsfc)*1e6:.2f} mg/(N s);  V9 = {float(p.V9):.1f}, V19 = {float(e['V19']):.1f} m/s")
print(f"eta_T = {float(p.eta_thermal):.3f}, eta_P = {float(p.eta_propulsive):.3f}")""",
        ),
        ("md", "## Bypass-ratio sweep (fixed core) and the ideal optima"),
        (
            "code",
            """\
alpha = np.linspace(0.0, 12.0, 121)
fig, ax = plt.subplots(figsize=(6, 3.8))
for pi_f in (1.5, 1.7, 2.0):
    q = turbofan(FL350, alpha, pi_f, 32.0, 1500.0, pi_cL=1.6, components=Components.modern())
    ax.plot(alpha, q.tsfc * 1e6, label=f"pi_f = {pi_f}")
ax.set_xlabel("bypass ratio"); ax.set_ylabel("TSFC [mg/(N s)]"); ax.set_ylim(15, 32); ax.legend()
plt.show()
ideal = dict(components=Components(), hot=AIR, include_fuel_mass=False)
a_star = float(optimum_bypass_ratio(FL350, 1.7, 30.0, 1600.0))
q = turbofan(FL350, a_star, 1.7, 30.0, 1600.0, **ideal)
print(f"ideal alpha* = {a_star:.3f}: V9 - V0 = {float(q.V9 - q.V0):.2f}, "
      f"(V19 - V0)/2 = {float(q.extras['V19'] - q.V0)/2:.2f} m/s")
pf_star = float(optimum_fan_pressure_ratio(FL350, 10.0, 30.0, 1600.0))
q = turbofan(FL350, 10.0, pf_star, 30.0, 1600.0, **ideal)
print(f"ideal pi_f* (alpha = 10) = {pf_star:.3f}: V9 = {float(q.V9):.2f}, V19 = {float(q.extras['V19']):.2f}")""",
        ),
    ],
    "05_off_design.ipynb": [
        (
            "md",
            """\
# 5 · Off-design performance and the real engines

The calibrated CFM56-7B26/3 and LEAP-1B28 models (ICAO databank data, one calibration each),
their LTO fuel flows, a cruise point, a hot day and degradation signatures.
Lesson: [05](../docs/lessons/05-off-design.md) ·
Theory: [off-design](../docs/off_design_performance.md) ·
[flight parameters](../docs/flight-parameters.md).""",
        ),
        ("code", SETUP + VALIDATION),
        ("md", "## Calibrated design points"),
        (
            "code",
            """\
for name in ENGINES:
    d = calibrated_engine(name).design_point
    print(f"{name:13s} BPR {d.alpha:.2f}  OPR {d.pi_c:.2f}  fan PR {d.pi_f:.3f}  "
          f"Tt4 {d.Tt4:.1f} K  airflow {d.mdot0:.1f} kg/s  TSFC {d.tsfc*1e6:.3f} mg/(N s)")""",
        ),
        ("md", "## ICAO LTO fuel flow: take-off is calibrated, the rest are predictions"),
        (
            "code",
            """\
for name in ENGINES:
    e, d = calibrated_engine(name), icao(name)
    for mode, frac in LTO_MODES:
        p = e.design_point if frac == 1.0 else e.operate_at_thrust(SLS, frac * d["rated_thrust"])
        ref = d["ff_" + mode]
        print(f"{name:13s} {mode:9s} model {p.fuel_flow:.4f}  ICAO {ref:.4f} kg/s  "
              f"({100*(p.fuel_flow/ref-1):+5.1f} %)  N1 {100*p.N1:5.1f} %  N2 {100*p.N2:5.1f} %")""",
        ),
        ("md", "## Cruise: corrected parameters"),
        (
            "code",
            """\
e = calibrated_engine("CFM56-7B26/3")
p = e.operate_at_thrust(FL350, 22e3)
print(f"Tt4 = {p.Tt4:.0f} K (Tt4/theta0 = {p.Tt4/(FL350.T0/288.15):.0f} K), alpha = {p.alpha:.2f}, "
      f"OPR = {p.pi_c:.1f}")
print(f"N1 = {100*p.N1:.1f} %, corrected N1 = {100*p.N1_corrected:.1f} %, "
      f"corrected flow = {p.corrected_flow:.1f} kg/s (take-off: {e.design_point.corrected_flow:.1f})")
print(f"TSFC = {p.tsfc*1e6:.2f} mg/(N s) = {tsfc_to_lb_per_lbf_h(p.tsfc):.3f} lb/(lbf h)")""",
        ),
        ("md", "## Hot day and component wear"),
        (
            "code",
            """\
hot = FlightCondition.sea_level_static(dT=15.0)
same = e.operate(hot, e.design_point.Tt4)
rated = e.operate_at_thrust(hot, e.design_point.thrust, start=same)
print(f"ISA+15 at the take-off Tt4: {100*same.thrust/e.design_point.thrust:.1f} % of rated thrust")
print(f"rated thrust needs Tt4 = {rated.Tt4:.0f} K and raises Tt45 by {rated.Tt45 - e.design_point.Tt45:.0f} K")
base = e.operate_at_thrust(SLS, e.design_point.thrust)
for field in ("e_f", "e_c", "e_t"):
    worn = e.with_components(e.components.with_(**{field: getattr(e.components, field) - 0.01}))
    q = worn.operate_at_thrust(SLS, e.design_point.thrust)
    print(f"{field} - 0.01: dTt45 = {q.Tt45 - base.Tt45:+5.1f} K, dWf = {100*(q.fuel_flow/base.fuel_flow-1):+.2f} %, "
          f"dN1 = {100*(q.N1-base.N1):+.2f}, dN2 = {100*(q.N2-base.N2):+.2f} % pts")""",
        ),
    ],
    "06_trade_studies.ipynb": [
        (
            "md",
            """\
# 6 · Trade studies

Lesson: [06](../docs/lessons/06-trade-studies.md) · Theory: [trade studies](../docs/trade_studies.md).""",
        ),
        (
            "code",
            SETUP
            + VALIDATION
            + """
from engines import ENGINE_COMPONENTS
from propulsion.trade_studies import sweep, fan_diameter
from propulsion.turbofan_model import turbofan
KW = dict(components=ENGINE_COMPONENTS, core_nozzle="convergent", fan_nozzle="convergent",
          pi_cL=1.6, pi_f_max=10.0)""",
        ),
        ("md", "## Cruise TSFC vs bypass ratio, each point with its best fan"),
        (
            "code",
            """\
alpha = np.linspace(1.0, 14.0, 27)
fig, ax = plt.subplots(figsize=(6, 3.8))
for opr in (25.0, 40.0):
    s = sweep(FL350, alpha, opr, 1300.0, **KW)
    ax.plot(alpha, s.tsfc[:, 0, 0] * 1e6, label=f"OPR {opr:.0f}")
ax.set_xlabel("bypass ratio"); ax.set_ylabel("TSFC [mg/(N s)]"); ax.legend(); plt.show()""",
        ),
        ("md", "## The price of bypass at 120 kN take-off thrust"),
        (
            "code",
            """\
for a in (1.0, 5.0, 9.0, 13.0):
    s = sweep(SLS, a, 35.0, 1450.0, **KW)
    mdot = 120e3 / s.specific_thrust.item()
    print(f"alpha {a:4.1f}: best fan {s.pi_f.item():.2f}, airflow {mdot:5.0f} kg/s, "
          f"fan diameter {float(fan_diameter(mdot, SLS)):.2f} m")""",
        ),
        ("md", "## The NOx price of pressure ratio (ICAO databank)"),
        (
            "code",
            """\
for name in ("CFM56-7B26/3", "CFM56-7B27/3", "LEAP-1B25", "LEAP-1B28"):
    Tt3 = float(calibrated_engine(name).design_point.cycle.stations["3"].T)
    d = icao(name)
    print(f"{name:13s} OPR {d['opr']:5.1f}  model Tt3 {Tt3:5.0f} K  NOx EI {d['nox_takeoff']:5.1f} g/kg  "
          f"({d['combustor']})")""",
        ),
    ],
}


def _merge_streams(outputs):
    """Join consecutive stdout/stderr chunks; how the kernel splits them depends on timing."""
    merged = []
    for out in outputs:
        prev = merged[-1] if merged else None
        if (
            prev is not None
            and out.get("output_type") == "stream"
            and prev.get("output_type") == "stream"
            and prev.get("name") == out.get("name")
        ):
            prev["text"] += out["text"]
        else:
            merged.append(out)
    return merged


def build(name: str, cells: list[tuple[str, str]]) -> Path:
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {
        "name": "python3",
        "display_name": "Python 3",
        "language": "python",
    }
    nb.cells = [
        nbformat.v4.new_markdown_cell(src) if kind == "md" else nbformat.v4.new_code_cell(src)
        for kind, src in cells
    ]
    for i, cell in enumerate(nb.cells):
        cell.id = f"cell-{i:02d}"  # stable ids keep rebuilds diff-free
    NotebookClient(
        nb,
        timeout=600,
        kernel_name="python3",
        record_timing=False,
        resources={"metadata": {"path": str(HERE)}},
    ).execute()
    for cell in nb.cells:
        cell.get("outputs", [])[:] = _merge_streams(cell.get("outputs", []))
    path = HERE / name
    nbformat.write(nb, path)
    return path


def main() -> None:
    for name, cells in NOTEBOOKS.items():
        print("built", build(name, cells).name)


if __name__ == "__main__":
    main()
