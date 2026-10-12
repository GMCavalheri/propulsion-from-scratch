# PLAN.md — AERO-03: Propulsion From Scratch

## Overview
A from-scratch thermodynamic and component-level performance model of gas turbine aircraft engines (turbojet and turbofan), built in Python. Third of five projects covering the classical pillars of aerospace engineering.

## Objective
Build a parametric engine cycle analysis tool that predicts thrust, specific fuel consumption, and off-design performance for turbojet and turbofan engines, validated against published performance data for real engines (e.g., CFM56, the engine family powering the Boeing 737NG).

## Why This Project
The Boeing 737 family runs on CFM56 (NG) and LEAP-1B (MAX) engines, and the RUL/fault-detection projects in this portfolio already deal with turbofan degradation data. This project builds the thermodynamic model *underneath* that data — understanding why EGT, N1/N2, and fuel flow behave the way they do, instead of only treating them as ML input features.

## Knowledge Covered
1. **Ideal Brayton Cycle**: implement the ideal turbojet cycle (compression, combustion, expansion, exhaust), compute thermal efficiency and specific thrust as functions of pressure ratio and turbine inlet temperature.
2. **Component-Level Modeling**: model each component (inlet, compressor, combustor, turbine, nozzle) individually with efficiency losses, enabling more realistic (non-ideal) cycle analysis.
3. **Turbofan Extension**: extend the model to a two-spool turbofan with bypass ratio as a parameter, compute thrust contributions from core and bypass streams separately.
4. **Off-Design Performance**: model how thrust and fuel consumption change with altitude, Mach number, and throttle setting (partial power) — this is what actually varies during a flight and what your RUL/reliability data reflects.
5. **Parametric and Trade Studies**: explore how bypass ratio, overall pressure ratio, and turbine inlet temperature trade off between thrust, efficiency, and (implicitly) noise/emissions — connecting to why modern engines like the LEAP-1B favor higher bypass ratios.

## Prerequisites / Background
- Thermodynamics: Brayton cycle, isentropic relations, compressible flow
- Basic gas dynamics (stagnation properties, Mach number relations)

## Data / Dataset
- **Public engine data**: ICAO Aircraft Engine Emissions Databank (rated thrust, bypass ratio, pressure ratio, and fuel flow at standard thrust settings for CFM56 and LEAP-1B variants); manufacturer public brochures and type-certificate data sheets (EASA/FAA TCDS) for published ratings.
- **Design charts**: turbofan trend charts from propulsion textbooks for qualitative comparison.
- **Atmosphere model**: International Standard Atmosphere (implemented from its published definition).
- Validation is trend-level and order-of-magnitude — detailed engine maps are proprietary and not used.

## Tech Stack
- Python, NumPy, SciPy
- Matplotlib for cycle diagrams (T-s, P-v), performance maps
- Pytest for validation against known cycle relations

## Repository Structure
```
propulsion-from-scratch/
  src/
    brayton_cycle/
    component_models/
    turbofan_model/
    off_design_performance/
  validation/          # comparison against published CFM56/LEAP-1B performance data
  notebooks/
  docs/
  tests/
```

## Execution Plan
- [x] **Phase 1 — Ideal Brayton cycle**: implement and validate thermal efficiency/specific thrust formulas against textbook closed-form results.
- [x] **Phase 2 — Component-level modeling**: add component efficiencies (compressor/turbine polytropic efficiency, combustor pressure loss), compare ideal vs. real cycle performance.
- [x] **Phase 3 — Turbofan extension**: implement the two-spool turbofan model with bypass ratio parameter, validate specific thrust/TSFC trends against published turbofan design charts.
- [x] **Phase 4 — Off-design performance**: model altitude/Mach/throttle effects on thrust and fuel flow, compare general trends against publicly available CFM56/LEAP-1B performance summaries.
- [x] **Phase 5 — Parametric trade studies**: sweep bypass ratio and pressure ratio, reproduce the classical trend toward high-bypass turbofans for fuel efficiency.
- [x] **Phase 6 — Documentation and publishing**: cycle diagrams, performance maps, and a written explanation connecting each model parameter to observable flight parameters (EGT, N1/N2, fuel flow).

## Validation Strategy
- Ideal cycle results checked against closed-form thermal efficiency/specific thrust equations.
- Turbofan trends (thrust, TSFC vs. bypass ratio) compared qualitatively against publicly available engine performance summaries and design textbooks.
- Off-design behavior checked for correct qualitative trends (thrust decreasing with altitude, TSFC increasing at low throttle, etc.).

## Deliverables
- Public repository with a documented, parametric turbofan performance model
- Validation report comparing model trends against published engine data
- Visualizations: T-s cycle diagrams, thrust/TSFC vs. bypass ratio and altitude, off-design performance maps

## Portfolio Differentiators
- Bridges reliability engineering on turbofan sensor data with first-principles propulsion theory — very few reliability/data engineers build the physics model behind the sensors they analyze.
- Uses real, in-service engine families (CFM56, LEAP-1B) as validation targets.

## Possible Extensions
- Add a simple emissions/NOx estimation model as a function of combustor conditions
- Feed this model's synthetic off-design data into the RUL Prediction project as an additional physics-informed data source
