# Trade studies

Code: [`src/propulsion/trade_studies/`](../src/propulsion/trade_studies),
[`validation/trade_studies.py`](../validation/trade_studies.py) ·
Notebook: [`06_trade_studies.ipynb`](../notebooks/06_trade_studies.ipynb) ·
Lesson: [6](lessons/06-trade-studies.md)

## Tools

- `best_fan_pressure_ratio(flight, alpha, pi_c, Tt4, pi_cL, pi_f_max, **cycle)`: the fan
  pressure ratio of minimum TSFC. Grid search (TSFC is undefined beyond the optimum, where the
  core runs out of energy), then a bounded refinement. In the ideal limit it reproduces
  $\tau_f^{\ast}$ to 10⁻⁶.
- `sweep(flight, alpha, pi_c, Tt4, ...)`: every combination on a meshgrid, each with its best
  fan; returns specific thrust, TSFC, efficiencies, $T_{t3}$, $P_{t3}$.
- `fan_diameter(mdot0, flight, M2=0.6, hub_tip=0.3)`: from
  $\dot m = \mathrm{MFP}(M_2)P_{t2}A/\sqrt{T_{t2}}$, $A = \frac{\pi}{4}D^2(1-h^2)$. Fan-face Mach and
  hub/tip ratio are assumptions.
- `jet_noise_index(perf, thrust)`: $10\log_{10}\sum\dot m V^7$ over both jets (Lighthill's
  eighth-power law, $W \propto \rho AV^8$). Relative ranking only.

## Main results (see [`validation/results/trade_studies.md`](../validation/results/trade_studies.md))

- Cruise TSFC falls with bypass ratio and OPR, with diminishing returns: α 1 → 5 gives −26 %,
  5 → 13 a further −12.5 % (120 kN class, OPR 35).
- The carpet's lower envelope runs to high α and high $T_{t4}$ together.
- The price at fixed take-off thrust: fan diameter 1.17 → 1.95 m (α 1 → 13). The bonus: jet
  noise index −20 dB.
- CFM56-7B26/3 → LEAP-1B28 cruise cycles: −11.0 % TSFC, of which OPR −2.7 %, $T_{t4}$ −1.1 % and
  the fan −7.5 % (order-dependent split).
- The NOx price (ICAO databank): take-off NOx EI 21.8 → 72.7 g/kg as the model's $T_{t3}$ rises
  808 → 920 K.

## Verification

[`tests/test_trade_studies.py`](../tests/test_trade_studies.py): the fan optimiser matches the
closed form; the sweep matches direct evaluation; the diameter inverts the MFP exactly; the
noise index obeys the 60 log10(V) scaling; and the classical trends hold.
