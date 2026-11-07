# Changelog

All changes to the fc-h743 hardware, its PX4 board port and its verification.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Hardware revisions are
letters (rev A, rev B); a tag `rev-A-draftN` marks a draft of rev A that has not been reviewed.

**Status: DRAFT until independent review. Do not order boards from any tag below.**

## [Unreleased]

## [rev-B-draft1] - 2026-11-08

Rev B: the primary IMU moves onto a thermally isolated island so the heater can hold it at a set
point. Everything below is simulated or rule-checked; nothing is built.

### Before and after
| | rev-A-draft3 | rev-B-draft1 |
|---|---|---|
| ICM-45686 location | B.Cu under the MCU | B.Cu on a slotted corner island (2 × 1 mm milled slots, copper-free edge bridges, 2.2 mm corner bridge) |
| Heater | 4 × 120 Ω 1206 in parallel, 0.86 W | 2 × 12 Ω 2010 in series on the island, 1.08 W (0.54 W per 0.75 W part) |
| Holdable IMU temperature window (routed copper, bench 25 °C + flight 15/35 °C) | **none** (−22.2 °C) | **45.6–57.8 °C** (12.1 °C) |
| Heater lift, prop wash | 6.7 °C | 39.6 °C |
| PX4 heater loop at the set point (15 °C flight) | cannot reach a set point | 0.52 °C steady error, ±0.34 °C takeoff transient |
| Set point (`HEATER1_TEMP`) | 45 °C | 51 °C |
| Hardware over-temperature cut-off | none | TMP302A on the island, trips at 60 °C |
| Isolation the loop tolerates | — | ≥ 83 % of the modelled value (first number to measure on a built board) |
| BMI088 | under the MCU, heated by the same ring | under the MCU, unheated; relies on PX4 thermal calibration |
| ERC / DRC / parity | 0/0 · 0 errors, 0 unconnected · 0 | same |
| +5V drop to the TPS2553 switches at their limits | 235 / 167 mV | 243 / 173 mV |
| Impedance of a track at the slot keepout | — | +0.8 Ω (1.1 %) |
| JLC BOM lines (`fab/bom_jlc.csv`) | 75 | 77 (12 Ω 2010 C3013299 replaces 120 Ω 1206; TMP302A C2877557 and 4.7 kΩ C25900 added) |

### Changed
- Heater: 2 × 12 Ω 2010 in series (R44 +5V→HEATER_MID, R45 HEATER_MID→HEATER_LO). Series keeps
  +5V and HEATER_LO on F.Cu across the corner bridge with no via. R46/R47 removed. Gate
  resistor R42 47 Ω → 4.7 kΩ so the cut-off can override the MCU.
- Q2 (heater MOSFET) moved to F.Cu near the corner bridge; CS pull-ups for the ICM-45686 moved off
  the island.
- Firmware: `HEATER1_TEMP` 45 → 51 °C. IMU rotation `-R 6` → `-R 14` (ROLL_180_YAW_270) for both
  IMUs: they are on the bottom side and PX4's drivers assume a top-side part, so rev A's yaw-only
  rotation left Z inverted. Still to confirm with a tilt test.
- Net classes: HEATER_LO and HEATER_MID in Supply (0.3 mm), 0.21 A.
- Schematic and board title blocks rev B.

### Added
- U23 TMP302A (+ C62): open-drain OUT on HEATER_G, trip 60 °C, 10 °C hysteresis.
- Board: two milled slots in Edge.Cuts, copper keepouts on the two edge bridges, 0.32 mm routing
  keepouts around the slots (`scripts/slot_keepout.py`).
- `sim/thermal/revB/island_routed.py` (rev A vs rev B on the routed copper), updated
  `heater_loop.py`, `sim/si/slot_edge.py` (atlc, track beside a slot), rev B IR drop.
- Scripts used for the rev B layout: `update_pcb.py` (scripted "update PCB from schematic"),
  `revb_island.py`, `revb_place3.py`, `revb_series.py`, `restore_bmi.py`, `lock_export_isl.py`,
  `viaspot.py`, `bridgecut.py`, `dedup.py`, `addcu.py`.

### Fixed
- Autorouter leftovers: 1,300+ zero-length and duplicate track segments removed; stray stubs the
  router added to USB, crystal and buck-boot nets removed so those nets match rev A exactly.

### Not done in rev B
- JLCDFM on the rev B Gerbers (the zip is ready; the browser pane cannot upload files).
- +5V trunk to the 5 V switches: no free corridor left of the MCU without rerouting ~20 nets.
- Inductor I_sat: no 4.7 µH part in the 5.4 × 5.2 mm footprint found above ~6.5 A; REVIEW item stays open.

### Rev B analysis (from the earlier unreleased entry)
- Requirement from the IMU datasheets: hold the ICM-45686 within ±1.5 °C (docs/revB_thermal.md).

### Rev A drafts (unreleased fixes before rev B)
- JLCDFM (2026-11-07) flagged GND stitching vias 0.37 mm from the 4 mm mounting holes. 21 stitching
  vias within 1 mm of a mounting-hole edge removed; DRC 0 errors, 0 unconnected, parity 0; no GND
  pour islands.
- Fab DFM results (JLCDFM) in docs/design_review.md; JLC quote settings in REVIEW.md.

## [rev-A-draft2] - 2026-11-06

Refinement round: vendor-guide review, field solvers, power-integrity and thermal checks, CI.

### Changed
- 5 V buck set point 4.98 V -> 5.09 V (R8 52.3 k -> 53.6 k, LCSC C53398). Reasons: the LM66100
  ideal-diode OR only prefers the buck when it sits above USB VBUS by more than its 80 mV
  turn-off threshold, and the IR-drop solver showed up to 235 mV of copper drop from the
  inductor to the TPS2553 switches at their current limits. Loop re-simulated: phase margin
  >= 66.6 deg, gain margin >= 13.1 dB; load step 4.78-5.39 V, below the 5.5 V rating of the
  parts on the rail.
- 328 track segments on VBAT_RAW, VBAT, +5V, +5V_FMU, +5V_PERIPH and +5V_CAN widened to the
  largest width clearance allows (`scripts/widen.py`). VBAT_RAW drop at 3 A: 66 -> 56 mV;
  +5V copper loss at full load: 630 -> 527 mW.
- Buck return path: GND vias added at output caps C11 and C12 and a second via at the B360A
  anode; D3, input and output cap GND pads and U1 GND tied solid into the pour (no thermal
  spokes), per the TPS54360B layout guidelines.

### Fixed (firmware)
- The 32 kHz IMU clock on PB10 was started before the sensor rail power-cycle, so it drove the
  ICM-45686's CLKIN pin while the sensor was unpowered. It now starts after `board_spi_reset()`
  and is parked (input, pull-down) whenever `board_peripheral_reset()` cuts +3V3_SENS.
- SPI2 (BMI088) had no power-enable pin in `spi.cpp`, so PX4 never parked the SPI2 pins while
  the shared +3V3_SENS rail was off; its chip-selects back-powered the BMI088. SPI2 now names
  PB2 too.

### Added
- `sim/si/`: atlc 2D field-solver cross-sections of the stackup (USB pair 84.7 ohm differential;
  single-ended 64-73 ohm), coupling vs gap, and a crosstalk scan of the routed board (worst
  case SD_CLK into CAN1_H, 1.1 % of swing).
- `sim/pi/`: DC IR-drop solver on the routed copper (VBAT_RAW, VBAT, +5V, +3V3).
- `sim/thermal/`: steady-state board temperature model in still air and prop wash.
- `scripts/export_geom.py`, `scripts/widen.py`.
- CI (`.github/workflows/hardware.yml`): ERC, DRC with schematic parity, pin-map check, KiBot
  fab package (JLCPCB Gerbers, drill, BOM, CPL), schematic PDF, interactive BOM, STEP; PX4
  build of the board port at the pinned PX4 commit; Simantic boot test when a token is set.
- CHANGELOG, CONTRIBUTING, issue and pull-request templates, docs/BUILD_LOG.md,
  docs/design_review.md.

### Found, not fixed in rev A (see REVIEW.md)
- IMU heater cannot hold a set point: the board is the heatsink. Model: IMUs at 53 C on the
  bench with no heater (above the 45 C set point), 33 -> 40 C in prop wash with the heater
  full on. Rev B: thermally isolate the IMU island; rev A relies on PX4 thermal calibration.
- +5V reaches the TPS2553 switches through a ~60 mm route around the MCU. Rev B: a direct trunk.
- Inductor saturation current (5 A) is below the TPS54360B switch current limit (5.5 A typ,
  6.8 A max).
- B360A catch diode reaches ~114 C case at 6S / 2.5 A in still air (rated 150 C).

## [rev-A-draft1] - 2026-10-31

First complete draft: schematic (ERC 0/0), 6-layer layout (DRC 0 errors, 0 unconnected, parity
0), 5 V buck loop simulation, PX4 board port and Simantic boot PASS, JLCPCB BOM 69/69 in stock.
