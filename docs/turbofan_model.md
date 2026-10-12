# Two-spool separate-exhaust turbofan

Code: [`src/propulsion/turbofan_model/`](../src/propulsion/turbofan_model) ·
Notebook: [`04_turbofan.ipynb`](../notebooks/04_turbofan.ipynb) ·
Lesson: [4](lessons/04-turbofan.md)

## Layout

Stations (SAE ARP755): 0 → 2 inlet → fan → 13; bypass 13 → 19 (fan nozzle); core 13 → booster
→ 25 → HPC → 3 → burner → 4 → HPT → 45 → LPT → 5 → 9 (core nozzle). The HPT drives the HPC; the
LPT drives the fan and the booster.

Inputs: bypass ratio α = $\dot m_{bypass}/\dot m_{core}$, fan pressure ratio $\pi_f$, overall
pressure ratio $\pi_c = P_{t3}/P_{t2}$, booster ratio $\pi_{cL}$, burner exit temperature
$T_{t4}$, components, gases and nozzle kinds. The HPC ratio follows as
$\pi_{cH} = \pi_c/(\pi_f\pi_{cL})$.

## Balances (per unit core flow)

```math
\eta_m(1+f)c_{pt}(T_{t4} - T_{t45}) = c_{pc}(T_{t3} - T_{t25}), \qquad
\eta_m(1+f)c_{pt}(T_{t45} - T_{t5}) = c_{pc}\left[(1+\alpha)(T_{t13} - T_{t2}) + (T_{t25} - T_{t13})\right]
```

```math
\frac{F}{\dot m_0} = \frac{F_{core} + F_{fan}}{(1+\alpha)\dot m_{core}}, \qquad S = \frac{f}{(1+\alpha)F/\dot m_0}
```

f is per unit *core* air; specific thrust is per unit *total* air. `extras` reports
`specific_thrust_core`, `specific_thrust_fan`, `thrust_ratio_fan`, `V19`, spool temperature and
pressure ratios, nozzle Mach numbers and pressures.

## Ideal-turbofan closed forms (Mattingly, *Elements of Propulsion*, Ch. 5)

```math
\left(\frac{V_9}{a_0}\right)^2 = \frac{2}{\gamma-1}\left[\tau_\lambda - \tau_r(\tau_c - 1 + \alpha(\tau_f - 1)) - \frac{\tau_\lambda}{\tau_r\tau_c}\right], \qquad
\left(\frac{V_{19}}{a_0}\right)^2 = \frac{2}{\gamma-1}(\tau_r\tau_f - 1)
```

- Best fan at fixed α: equal jet speeds $V_{19} = V_9$,
  $\tau_f^{\ast} = [\tau_\lambda - \tau_r(\tau_c-1) - \tau_\lambda/(\tau_r\tau_c) + \alpha\tau_r + 1]/[\tau_r(1+\alpha)]$.
- Best bypass at fixed $\pi_f$: $V_9 - V_0 = \frac12(V_{19} - V_0)$,
  $\alpha^{\ast} = [\tau_\lambda - \tau_r(\tau_c-1) - \tau_\lambda/(\tau_r\tau_c) - \frac14(\sqrt{\tau_r\tau_f-1} + \sqrt{\tau_r-1})^2]/[\tau_r(\tau_f-1)]$.
- With losses the best fan leaves $V_{19}/V_9 \approx \eta_{LPT}\eta_m\eta_f$.

`ideal_jet_velocities`, `optimum_bypass_ratio`, `optimum_fan_pressure_ratio`.

## Verification

[`tests/test_turbofan.py`](../tests/test_turbofan.py): α = 0 reproduces the turbojet exactly;
the ideal limit matches the closed forms; the booster/HPC split is irrelevant when ideal;
200,001-point searches recover α* and $\pi_f^{\ast}$ with the jet-velocity conditions to 10⁻⁹;
both spool balances close; core + fan thrust = total; bypass raises ηP; convergent nozzles keep
ηP < 1.
