# Changelog

All changes to the fc-h743 hardware, its PX4 board port and its verification.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Hardware revisions are
letters (rev A, rev B); a tag `rev-A-draftN` marks a draft of rev A that has not been reviewed.

**Status: DRAFT until independent review. Do not order boards from any tag below.**

## [Unreleased]

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
