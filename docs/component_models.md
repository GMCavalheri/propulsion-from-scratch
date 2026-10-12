# Component models and the non-ideal turbojet

Code: [`src/propulsion/component_models/`](../src/propulsion/component_models) ·
Notebook: [`03_component_models.ipynb`](../notebooks/03_component_models.ipynb) ·
Lesson: [3](lessons/03-real-components.md)

## Figures of merit (`Components`)

| Field | Meaning | `Components()` | `Components.modern()` (assumption) |
|---|---|---|---|
| `pi_d_max`, `inlet_shock_losses` | inlet $P_t$ ratio; MIL-E-5007 ram recovery on/off | 1, off | 0.995, on |
| `e_c`, `e_f`, `e_t` | polytropic efficiencies: compressors, fan, turbines | 1 | 0.90, 0.89, 0.89 |
| `pi_b`, `eta_b` | burner $P_t$ ratio, combustion efficiency | 1 | 0.96, 0.995 |
| `eta_m` | mechanical efficiency per spool | 1 | 0.99 |
| `pi_n`, `pi_fn` | core / fan nozzle $P_t$ ratios | 1 | 0.99 |

`Components()` is ideal and reproduces the ideal turbojet exactly (with `hot=AIR`,
`include_fuel_mass=False`). The `modern()` values are chosen inside the ranges Mattingly
(*Elements of Propulsion*, Ch. 6) tabulates; they describe no particular engine.

## Relations

- **Inlet**: $\pi_d = \pi_{d,max}\eta_r$, with $\eta_r = 1 - 0.075(M_0-1)^{1.35}$ for $1 < M_0 \le 5$
  and $800/(M_0^4 + 935)$ above (MIL-E-5007D).
- **Compressor**: $\tau_c = \pi_c^{(\gamma-1)/(\gamma e_c)}$, $\eta_c = (\pi_c^{(\gamma-1)/\gamma} - 1)/(\tau_c - 1) < e_c$ (preheat).
- **Turbine**: $\pi_t = \tau_t^{\gamma/((\gamma-1)e_t)}$, $\eta_t = (1-\tau_t)/(1-\tau_t^{1/e_t}) > e_t$ (reheat).
- **Burner** (enthalpies from the heating-value datum $T_{ref}$ = 298.15 K):

```math
f = \frac{c_{pt}(T_{t4} - T_{ref}) - c_{pc}(T_{t3} - T_{ref})}{\eta_b h_{PR} - c_{pt}(T_{t4} - T_{ref})}
```

  `T_ref=0` gives the textbook form, which over-counts $(c_{pt}-c_{pc})T_{ref}$ ≈ 70 kJ/kg of heat
  when the gases differ (found by the ICAO validation; see Lesson 3).
- **Shaft**: $\eta_m(1+f)c_{pt}(T_{t4} - T_{t5}) = c_{pc}(T_{t3} - T_{t2})$.
- **Nozzle** (`nozzle_exit`): `"ideal"` expands to $P_0$; `"convergent"` chokes when
  $P_{t9}/P_0 > ((\gamma+1)/2)^{\gamma/(\gamma-1)}$ and adds pressure thrust
  $(1+f)R_tT_9(1 - P_0/P_9)/V_9$. Full expansion maximises gross thrust ($dF_g = (P_9-P_0)dA_9$).
- **Efficiencies**: jet power uses the *fully expanded* jet velocity, so under-expansion shows as
  a propulsive loss and $\eta_P < 1$.

`turbojet(flight, pi_c, Tt4, components, cold, hot, h_PR, nozzle, include_fuel_mass)` returns a
`CyclePerformance`; `extras` holds πd, τc, τt, πt, ηc, ηt, M9, P9 and the fully expanded V9.

## Verification

[`tests/test_component_models.py`](../tests/test_component_models.py): exact ideal limit at three
flight conditions; stacking 20,000 stages of efficiency e recovers the polytropic relation;
burner balance in both datum conventions; entropy rises through every lossy component; shaft
and energy balances close; full expansion beats a convergent nozzle; TSFC has a finite-πc
minimum with losses and none without; TSFC is undefined (NaN) without thrust.
