# Off-design performance

Code: [`src/propulsion/off_design_performance/`](../src/propulsion/off_design_performance) ·
Notebook: [`05_off_design.ipynb`](../notebooks/05_off_design.ipynb) ·
Lesson: [5](lessons/05-off-design.md)

## Model (after Mattingly, *Elements of Propulsion*, Ch. 8)

`TurbofanEngine.design(flight, alpha, pi_f, pi_c, Tt4, pi_cL, thrust=... | mdot0=...)` runs the
on-design cycle (convergent nozzles) and freezes:
- the HPT nozzle flow capacity $C_4 = \dot m_4\sqrt{T_{t4}}/P_{t4}$ (choked);
- the HPT temperature ratio $\tau_{tH}$ (choked HPT and LPT nozzles at constant efficiency);
- the booster-to-fan work ratio $(T_{t25} - T_{t13})/(T_{t13} - T_{t2})$;
- the core and fan nozzle throat areas $A_9$, $A_{19}$;
- the design fan and HPC enthalpy rises (for the spool-speed estimate).

`operate(flight, Tt4)` solves four unknowns ($\ln\pi_f$, $\ln\pi_{cL}$, $\ln\pi_{cH}$, $\ln\alpha$)
from four residuals: $\tau_{tH}$ fixed; booster/fan work ratio fixed;
$\alpha\dot m_c = A_{19}\mathrm{MFP}(M_{19})P_{t19}/\sqrt{T_{t13}}$ with
$\dot m_c(1+f) = C_4P_{t4}/\sqrt{T_{t4}}$; $\dot m_c(1+f) = A_9\mathrm{MFP}(M_9)P_{t9}/\sqrt{T_{t5}}$.
The spool balances hold by construction (the on-design function computes $T_{t45}$, $T_{t5}$).
Solver: `scipy.optimize.root` (hybr), with continuation in flight condition and $T_{t4}$ when a
direct solve fails. `operate_at_thrust(flight, F)` marches $T_{t4}$ until the target is
bracketed, then uses Brent's method.

Component polytropic efficiencies and loss ratios stay at design values (no maps). Spool speeds:
$(N/N_d)^2$ = fan (N1) or HPC (N2) enthalpy rise over its design value.

## Outputs (`OperatingPoint`)

`thrust`, `fuel_flow`, `tsfc`, `alpha`, `pi_f`, `pi_cL`, `pi_cH`, `pi_c`, `mdot_core`, `mdot0`,
`N1`, `N2`, `N1_corrected` (= N1/√θ2), `corrected_flow` (= ṁ0√θ2/δ2), `Tt45`, `Tt5`, the full
`cycle` and `converged`.

## Similarity

At equal $M_0$ and $T_{t4}/T_0$ the engine runs at the same corrected point:
$F/\delta_0$, $\dot m\sqrt\theta/\delta$, $N/\sqrt\theta$ and all pressure ratios are equal. This is
exact with the fuel mass neglected, and close otherwise.

## Calibrated real-engine models

[`validation/engines.py`](../validation/engines.py) builds the CFM56-7B26/3 and LEAP-1B28 from
the ICAO databank (BPR, OPR, rated thrust), with the best fan and $T_{t4}$ calibrated to the
ICAO take-off fuel flow. See the [validation report](validation-report.md).

## Verification

[`tests/test_off_design.py`](../tests/test_off_design.py): exact design-point reproduction; the
choked HPT capacity and $\tau_{tH}$ hold to 10⁻⁸, and the LPT nozzle capacity (never imposed)
does too; path independence; exact corrected similarity; throttle trends (thrust, N1, N2 fall,
α rises, N1 < N2, TSFC bucket); lapse with altitude and speed; `operate_at_thrust` accuracy.
