# Ideal Brayton cycle and ideal turbojet

Code: [`src/propulsion/brayton_cycle/`](../src/propulsion/brayton_cycle) ·
Notebook: [`02_ideal_brayton_cycle.ipynb`](../notebooks/02_ideal_brayton_cycle.ipynb) ·
Lesson: [2](lessons/02-ideal-brayton-cycle.md)

## Closed cycle

Isentropic compression and expansion, heat added and rejected at constant pressure, one gas.
With $\tau = \pi^{(\gamma-1)/\gamma}$ and $\tau_\lambda = T_{max}/T_{min}$:

```math
\eta_{th} = 1 - \frac{1}{\tau}, \qquad \frac{w_{net}}{c_pT_{min}} = \tau_\lambda\left(1 - \frac{1}{\tau}\right) - (\tau - 1), \qquad \tau^{\ast} = \sqrt{\tau_\lambda}
```

`brayton_thermal_efficiency`, `brayton_specific_work`, `brayton_optimum_tau`.

## Ideal turbojet (Mattingly, *Elements of Propulsion*, Ch. 5)

Assumptions: isentropic components, burner at constant $P_t$, one perfect gas, $P_9 = P_0$,
fuel mass neglected in the balances (f is reported). With
$\tau_r$, $\tau_c = \pi_c^{(\gamma-1)/\gamma}$, $\tau_\lambda = T_{t4}/T_0$:

```math
\tau_t = 1 - \frac{\tau_r}{\tau_\lambda}(\tau_c - 1), \qquad
\left(\frac{V_9}{a_0}\right)^2 = \frac{2}{\gamma-1}\frac{\tau_\lambda}{\tau_r\tau_c}(\tau_r\tau_c\tau_t - 1), \qquad
\frac{F}{\dot m_0} = a_0\left(\frac{V_9}{a_0} - M_0\right)
```

```math
f = \frac{c_pT_0}{h_{PR}}(\tau_\lambda - \tau_r\tau_c), \quad S = \frac{f}{F/\dot m_0}, \quad
\eta_T = 1 - \frac{1}{\tau_r\tau_c}, \quad \eta_P = \frac{2M_0}{V_9/a_0 + M_0}, \quad \eta_O = \eta_T\eta_P
```

Maximum specific thrust at $\tau_c^{\ast} = \sqrt{\tau_\lambda}/\tau_r$, where $T_9 = T_{t3}$
(`optimum_compressor_pressure_ratio`). For $\tau_c^{\ast} < 1$ the best engine is a ramjet.

`ideal_turbojet(flight, pi_c, Tt4)` broadcasts over `pi_c` and `Tt4` and returns a
`CyclePerformance`: `specific_thrust` [N·s/kg], `tsfc` [kg/(N·s)], `f`, the three efficiencies,
`V0`, `V9`, `stations` (static at 0 and 9, stagnation elsewhere) and `extras` (τ ratios).
TSFC is NaN wherever specific thrust is not positive. `ts_diagram(perf)` returns the T–s path.

## Verification

All closed-form identities ([`tests/test_brayton_cycle.py`](../tests/test_brayton_cycle.py)):
turbine work = compressor work; KE gain / fuel energy = $1 - 1/(\tau_r\tau_c)$ to 7×10⁻¹⁶;
$\eta_O = \eta_T\eta_P$; isentropic stations share one entropy; a 400,001-point search finds
the closed-form optimum; f and thrust vanish together at $\tau_r\tau_c = \tau_\lambda$; ramjet and
static limits.
