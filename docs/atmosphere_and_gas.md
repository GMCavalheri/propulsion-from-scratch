# Atmosphere and gas dynamics

Code: [`src/propulsion/atmosphere/`](../src/propulsion/atmosphere),
[`src/propulsion/gas/`](../src/propulsion/gas), [`src/propulsion/flight.py`](../src/propulsion/flight.py),
[`src/propulsion/units.py`](../src/propulsion/units.py) ·
Notebook: [`01_atmosphere_and_gas.ipynb`](../notebooks/01_atmosphere_and_gas.ipynb) ·
Lesson: [1](lessons/01-atmosphere-and-compressible-flow.md)

## International Standard Atmosphere

Hydrostatics plus the perfect-gas law, with the temperature profile defined piecewise linear in
geopotential altitude H (ICAO Doc 7488 / US Standard Atmosphere 1976):

| Layer | H base [m] | T base [K] | λ [K/m] |
|---|---|---|---|
| troposphere | 0 | 288.15 | −0.0065 |
| tropopause | 11,000 | 216.65 | 0 |
| stratosphere | 20,000 | 216.65 | +0.001 (to 32 km) |

```math
\lambda \neq 0:\ \frac{P}{P_b} = \left(\frac{T}{T_b}\right)^{-g_0/(R\lambda)}, \qquad
\lambda = 0:\ \frac{P}{P_b} = \exp\left[-\frac{g_0(H - H_b)}{R T_b}\right], \qquad
H = \frac{r_0 z}{r_0 + z}
```

with $g_0$ = 9.80665 m/s², $r_0$ = 6,356,766 m and R = 8314.32/28.9644 J/(kg·K) (the US 1976
definition; ICAO prints 287.05287, which differs by 7×10⁻⁷). `isa(h, dT, geopotential)` returns T, P,
ρ, a and the ratios θ, δ, σ; `dT` shifts the temperature at fixed pressure (ISA+ΔT day).
`pressure_altitude(P)` inverts it. Flight levels are pressure altitudes: use
`geopotential=True` with the flight level in metres.

## Gas model

Calorically perfect gases, `Gas(cp, gamma)`, with R = cp(γ−1)/γ. Cycle analysis uses two
(assumptions, after Mattingly, *Elements of Propulsion*, Ch. 7):

| | cp [J/(kg·K)] | γ | used for |
|---|---|---|---|
| `AIR` | 1004 | 1.40 | free stream to station 3 |
| `COMBUSTION_GAS` | 1239 | 1.30 | station 4 to the core nozzle |

`H_PR_JET_A` = 42.8 MJ/kg. `entropy_change(gas, T1, P1, T2, P2)` = cp ln(T2/T1) − R ln(P2/P1).

## One-dimensional isentropic flow

```math
\frac{T_t}{T} = 1 + \frac{\gamma-1}{2}M^2, \quad \frac{P_t}{P} = \left(\frac{T_t}{T}\right)^{\frac{\gamma}{\gamma-1}}, \quad
\frac{A}{A^{\ast}} = \frac{1}{M}\left[\frac{2}{\gamma+1}\frac{T_t}{T}\right]^{\frac{\gamma+1}{2(\gamma-1)}}, \quad
\mathrm{MFP} = \frac{\dot m\sqrt{T_t}}{P_t A} = M\sqrt{\frac{\gamma}{R}}\left(\frac{T_t}{T}\right)^{-\frac{\gamma+1}{2(\gamma-1)}}
```

MFP peaks at M = 1 (choking); a choked throat fixes $\dot m\sqrt{T_t}/P_t$. Functions:
`stagnation_temperature_ratio`, `stagnation_pressure_ratio`, `mach_from_pressure_ratio`,
`area_ratio`, `mach_from_area_ratio(subsonic/supersonic)`, `mass_flow_parameter`.

## Flight condition

`FlightCondition(M0, T0, P0)` or `FlightCondition.at_altitude(h, M0, dT, geopotential)` gives
$a_0$, $V_0$, the ram ratios $\tau_r = 1 + \frac{\gamma-1}{2}M_0^2$, $\pi_r = \tau_r^{\gamma/(\gamma-1)}$ and
$T_{t0}$, $P_{t0}$.

## Units

`propulsion.units` holds exact conversion factors (NIST SP 811): `LB`, `LBF`, `FT`, `KT` and the
TSFC conversions (1 lb/(lbf·h) = 28.325 mg/(N·s)).

## Verification

ISA matches the US 1976 tables to every printed digit (e.g. 22,632.06 Pa at 11 km); hydrostatic
balance holds to 10⁻⁶ by finite differences; isentropic ratios match Anderson's tables; every
inverse round-trips ([`tests/test_atmosphere.py`](../tests/test_atmosphere.py),
[`tests/test_gas.py`](../tests/test_gas.py)).
