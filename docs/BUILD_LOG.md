# Build log: fc-h743, from spec to rev A

**Status: DRAFT until independent review. Nothing has been ordered.**

Each step lists the tool used, what it found, and what changed in the design because of it.
Details for every check are in [verification.md](verification.md) and
[design_review.md](design_review.md).

## 1. Spec and reference design
- **Input:** a written spec for a 38 × 38 mm, 4-layer, top-only flight controller with an H7 MCU, two
  IMUs, a baro, CAN, DShot, microSD and USB, built from JLCPCB stock.
- **Reference:** Pixhawk FMUv6C (STM32H743 in LQFP-100) instead of FMUv6X (STM32H753, 176-ball BGA).
  FMUv6C gives PX4 pin roles, drivers and a board port to start from.
- **Added for learned control:** ICM-45686 clocked from the MCU (TIM2_CH3, 32 kHz), BMI088 on its own
  bus, bidirectional DShot, 2 × CAN FD, camera trigger/capture timers, switchable sensor rail.

## 2. Tooling
KiCad 9.0.8 (kicad-cli + pcbnew Python in an Ubuntu 26.04 chroot, because the 24.04 workspace stops
at KiCad 7), Python generators in `scripts/`, ngspice 45.2, Freerouting 1.9.0, the JLCPCB parts API,
PX4 and Simantic 0.8.7 on a Mac.
- Freerouting 2.5.0 did not converge; 1.9.0 did.
- KiCad crashed saving after its own Specctra import → custom importer `import_ses.py`.
- pcbnew resets net classes in the project file on save → the reviewed project file is restored after
  every save.
- STM32CubeMX needs an ST login → `pinmap_check.py` checks alternate functions against ST's pin data.

## 3. Pin map first
`pinmap_check.py` checks every pin's alternate function and flags any peripheral signal claimed twice.
**PASS, 74 pins.** Changes from FMUv6C: BMI088 to SPI2 (FRAM dropped, params on SD), PB10 to TIM2_CH3,
PE12/PB12 to CAN standby, UART8 RX to ESC telemetry, USART6 to RC. Timers planned by hand (all DShot on
TIM1, TIM8 left for PX4's HRT).

## 4. Parts and BOM
69 unique parts, 176 placements, every one by LCSC number. JLC parts API: 69/69 in stock (first check
2026-10-31, re-checked 2026-11-06). Thinnest lines today: R5 714, microSD socket 955 (down from 19,222),
ICM-45686 1,717.

## 5. Schematic and ERC
`design.py` holds every part, value and net. `gen_lib.py` builds the missing symbols and footprints,
`gen_sch.py` writes a 7-sheet label-style schematic. ERC findings go back into the generator, never into
hand edits. **ERC 0 errors, 0 warnings.**

## 6. Buck loop (ngspice)
Averaged peak-current-mode model of the TPS54360B, 27 corners (load × output capacitance × sampling-pole
Q). First compensation (13.3 k / 3.9 n / 39 p) crossed over at up to 53 kHz with 10 dB gain margin →
**9.09 k / 4.7 n / 47 p**: crossover 19–36 kHz, PM ≥ 66°, GM ≥ 12.9 dB (rev-A-draft1 set point).

## 7. Size, stackup, placement
Courtyards alone filled 94 % of 38 × 38 mm → **50 × 50 mm**. Four layers leave two routing layers →
**6 layers**, JLC06161H-3313D, thicknesses from jlcpcb.com/impedance written into the board file
(F sig / In1 GND / In2 sig / In3 sig / In4 GND / B sig). IMUs on the bottom inside the MCU's pin ring;
buck in the far corner. Findings: USB-C tabs under the microSD → microSD to the left edge; an MCU keep-out
ring blocked routing → removed.

## 8. Routing and DRC
Net classes first (HighCurrent 0.8 mm, Power 0.4, Supply 0.3, USB 0.25/0.15, signals 0.127/0.1).
A custom A* router proved routability; Freerouting 1.9 did the main pass. DRC and a union-find GND
check (`gnd_graph.py`) then found silent opens, GND pour islands, clearance errors and a 0.15 mm VBAT
segment → corridor re-runs, a local router (`fix_route.py`), stitching vias, reroutes.
**DRC 0 errors, 0 unconnected, parity 0.**

## 9. Critical nets by hand
`check_critical.py` measured what DRC does not: switch node 20 mm of track with vias → re-placed power
stage and a 26 mm² pour with keep-out; boot loop 17 → 2.3 mm; crystal 19.6 mm with 4 vias → 6.1 / 4.1 mm,
no vias; trapped VIN pin → VIN pour; C8 dropped (C3 under the VIN vias); USB mismatch 5.7 → 2.3 mm.

## 10. PX4 on the netlist (Simantic)
Board port written from the pin map; `gen_scenario.py` attaches sensor models to the buses, chip selects
and addresses the netlist gives. Found and fixed: a missing `BOARD_ADC_BRICK_VALID`, params pointed at
a FRAM the board lacks, old parameter names, an SD write stall caused by the model (sim-only build flag).
**PASS:** ICM-45686 on SPI1, BMI088 on SPI2, BMP581 on I2C4 @ 0x47, DroneCAN on CAN1, logger, NSH.

## 11. Refinement round (rev-A-draft2)
| Tool | Found | Changed |
|---|---|---|
| Vendor datasheets | LM66100 OR only prefers the buck if it is 0–80 mV above USB; buck at 4.98 V | set point 5.09 V (R8 53.6 k); 5.19 V tried first, peaked at 5.50 V on load release |
| TPS54360B layout guide | diode anode 1 via, C11/C12 none, pads on thermal spokes | vias added, pads solid |
| BMP581 datasheet (pins high with VDDIO off) | 32 kHz clock ran during the sensor-rail reset; SPI2 pins never parked | firmware: clock after reset and parked on rail-off; SPI2 power pin |
| atlc 2D field solver | open boundary gave nonsense; then USB 84.7 Ω, signals 64–73 Ω | grounded enclosure in the model; no layout change |
| Crosstalk scan | worst SD_CLK → CAN1_H 1.1 % | none |
| IR-drop solver | +5V to the 5 V switches 279 / 203 mV at their limits | 328 segments widened (235 / 167 mV); set point covers the rest; rev-B trunk |
| Thermal model | 86 °C board, ~114 °C diode at 6S in still air; heater cannot regulate | REVIEW items; rev-B IMU island |
| PX4 builds (Linux + macOS) | builds at c0d2c54, flash 91 % | CI firmware job |
| Simantic re-run | same PASS with the patched firmware | — |
| KiBot + GitHub Actions | first runs on a clean runner failed where the workspace passed: no KiCad symbol tables (580 ERC warnings), no ARM newlib (PX4 link), no lxml (KiBot), a 38-min PPA stall | library tables seeded, packages named explicitly, `.deb` cache + step timeout; only "stock footprint library not installed" is filtered (footprints are embedded and DRC checks parity) |

## Open before ordering
- Owner: licence choice, JLCPCB and second-fab DFM (logins), `SIMANTIC_TOKEN` secret, an independent
  reviewer.
- Reviewer decisions: IMU heater, +5V route, inductor I_sat, diode temperature.
- Bench: 32 kHz on PB10, sensor pins ≤ 0.3 V with the rail off, DShot telemetry port, 5 V load step,
  IMU rotation.
