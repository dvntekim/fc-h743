# 5 V buck: loop and transient simulation

Part: TI TPS54360B (60 V, 3.5 A, peak-current mode), 597 kHz (RT = 162 kΩ), L = 4.7 µH (FXL0530),
Cout = 3 × 22 µF 0805 X5R (derated), catch diode B360A, input 2S–6S.
Output: 0.8 V × (1 + 53.6 k / 10 k) = **5.09 V** (raised from 4.98 V in rev-A-draft2; see CHANGELOG).

Model: averaged current-mode small-signal model (Ridley) in ngspice 45.2: `sim/buck/loop.py` (Bode) and
`sim/buck/step.py` (large-signal load step). Numbers in `sim/buck/loop_results.json`.

| Compensation (Rc / Cc / Cp) | Crossover | Worst phase margin | Worst gain margin |
|---|---|---|---|
| 13.3 kΩ / 3.9 nF / 39 pF | 27–52 kHz | 60.0° | 10.2 dB |
| 13.3 kΩ / 4.7 nF / 39 pF | 27–52 kHz | 60.6° | 10.2 dB |
| **9.09 kΩ / 4.7 nF / 47 pF (built)** | **19–35 kHz** | **66.6°** | **13.1 dB** |

Corners: load 0.3 / 1.5 / 3.5 A × effective output capacitance 27 / 39 / 51 µF (DC-bias derating spread) × Q of the sampling double pole 0.5 / 1 / 2.
Crossover stays below fsw/15 at every corner.

Load step 0.25 → 2.45 → 0.25 A at 1 A/µs (`step.py`): +5V moves between **4.78 V and 5.39 V**
(5.09 V steady state). The load-release peak stays under the 5.5 V recommended maximum of the
LM66100, TLV62569, LP5907 and TCAN1462V. (A 5.19 V set point was tried first: its peak reached 5.50 V.)

Limits of the model: averaged (no ripple), ideal current sense, no input-filter interaction. A load step on the real board with a scope on +5V (bench test T2 in the spec covers ripple) is still the decider.
