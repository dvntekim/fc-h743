# Verification log — fc-h743 rev A

Status: **DRAFT UNTIL INDEPENDENT REVIEW.** Every check below was run by tools; none replaces a second engineer.

## 1. Electrical rules (KiCad 9.0.8 ERC)
`kicad-cli sch erc --severity-all` → **0 errors, 0 warnings** (`docs/reports/erc.rpt`).

## 2. Design rules (KiCad 9.0.8 DRC, JLCPCB 6-layer limits)
`kicad-cli pcb drc --severity-all --schematic-parity` → **0 errors, 0 unconnected items, 0 schematic-parity issues**
(`docs/reports/drc.rpt`). 61 warnings remain, all silkscreen cosmetics (reference text touching
another outline or a pad; the fab clips silk off pads). Rules in force:

| Rule | Value | JLCPCB 6-layer capability |
|---|---|---|
| Min track / clearance | 0.10 / 0.10 mm (signals 0.127 mm) | 0.09 / 0.09 mm |
| Vias | 0.45/0.20 mm (500); 0.35/0.15 mm (20, of which 17 via-in-pad) | 0.15 mm drill / 0.25 mm pad; via-in-pad = epoxy fill + cap |
| Annular ring | ≥ 0.10 mm | 0.075 mm |
| Copper to edge | 0.30 mm, plus a 0.55 mm no-track/no-via ring | 0.3 mm |
| Hole to hole | 0.25 mm | 0.2 mm |
| Thermal spokes | ≥ 1 (custom rule in `kicad/fc.kicad_dru`) | — |

Board: 50 × 50 mm, 6 layers, 1.6 mm, JLC06161H-3313D (stackup in the board file, cross-checked against
jlcpcb.com/impedance on 2026-10-31: 3313+1080 / 0.25 core / 7628+2116+7628 / 0.25 core / 1080+3313), ENIG.
554 vias, ~3 500 track segments, GND pours on all signal layers stitched to the In1/In4 planes.

An extra connectivity pass (`scripts/gnd_graph.py`, union-find over pours, tracks, vias and pads) finds
no isolated GND copper that carries a pad.

## 3. Layout checks that DRC does not do
See `docs/critical_nets.md` (generated from the routed board). Highlights:
- Switch node is a 26 mm² F.Cu pour joining TPS54360B SW, B360A cathode, inductor and boot cap; a keepout
  stops any other track or via crossing it. Boot loop 2.3 mm.
- 16 MHz crystal: 3 mm from the MCU, HSE_IN 6.1 mm / HSE_OUT 4.1 mm on F.Cu, no vias, load caps at the pads.
- IMUs are 16 mm from the inductor and 14 mm from the buck IC (spec ≥ 10 mm). No sensor or clock net crosses L1 on any layer.
- USB FS pair 0.25/0.15 mm on F.Cu over In1 GND; D+ uses one via pair to cross D− at the ESD array (fine at 12 Mbit/s).
- VIN: F.Cu pour from the VBAT vias to U1 pin 2; HF input cap C3 directly under those vias.

## 4. Pin map
`scripts/pinmap_check.py` checks every alternate function against ST's pin data (KiCad
`MCU_ST_STM32H743VITx` symbol): **PASS, 74 pins** (`docs/pinmap.md`).

## 5. BOM
Every LCSC part in stock at JLCPCB on 2026-10-31 (`docs/bom_check.md`).

## 6. 5 V buck (ngspice 45.2)
Averaged current-mode model of the TPS54360B with the chosen compensation (9.09 kΩ / 4.7 nF / 47 pF) at
the 5.09 V set point, 27 corners (load 0.3–3.5 A, effective Cout 27–51 µF, sampling-pole Q 0.5–2):
crossover 19–35 kHz, phase margin ≥ 66.6°, gain margin ≥ 13.1 dB. 0.25 → 2.45 A step at 1 A/µs:
4.78–5.39 V (`docs/power_sim.md`, `sim/buck/`).

## 7. PX4 on the netlist (Simantic 0.8.7, STM32H743VI model)
`sim/simantic/scenario.yaml` is generated from the netlist (`scripts/gen_scenario.py`): bus, chip select
and address of every sensor come from `design.py`, so a wiring or pin-map mistake makes the firmware miss
its sensor. Firmware: PX4 main (1.18.0-80) with the `dvntekim_fch743` board port in `firmware/`.

Result: **PASS, 5 expected strings present, 2 forbidden absent** (re-run 2026-11-06 on the rev-A-draft2 firmware with the sensor-rail fixes: same result) (`docs/reports/simantic_console.txt`):
```
icm45686 #0 on SPI bus 1 rotation 6        <- SPI1, CS PC13 (WHO_AM_I 0xE9 read back)
bmi088_accel #0 on SPI bus 2 rotation 6    <- SPI2, CS PC15
bmi088_gyro #0 on SPI bus 2 rotation 6     <- SPI2, CS PC14
bmp581 #0 on I2C bus 4 address 0x47        <- I2C4
INFO [uavcan] advertising node_id 42       <- FDCAN1 receives the DroneCAN peer
INFO [logger] logger started               <- SDMMC2 card mounted and writable
NuttShell (NSH) NuttX-12.12.0
```
Expected in simulation: "No valid data" preflight warnings (the sensor peers answer identification
registers but stream no samples), and the heater waiting for accel data.

Found and fixed by the simulator before any copper was ordered:
1. `BOARD_ADC_BRICK_VALID` undefined for a one-brick board — build failure.
2. Parameter storage pointed at a FRAM this board does not have — `CONFIG_BOARD_PARAM_FILE` now on the SD card.
3. No default airframe — `SYS_AUTOSTART 4001`; heater/DShot parameter names updated to PX4 1.18 (`HEATER1_TEMP`, `PWM_MAIN_TIM0 = -6` for BDShot600).

Open items the simulator raised (see REVIEW.md):
- The 32 kHz IMU clock on PB10 measured 16 kHz in the model. Either the model clocks TIM2 at PCLK1
  instead of 2×PCLK1, or the ARR is off by 2×. Scope it on the bench.
- `dshot telemetry` could not open `/dev/ttyS6` (UART8) in the model. Check `DSHOT_TEL_CFG` on hardware.
- The simulator build disables `CONFIG_MMCSD_SDIOWAIT_WRCOMPLETE` (its SDMMC model never raises the
  D0-busy-end interrupt); the hardware build keeps it. Both builds compile.

## 8. Vendor guides (rev-A-draft2)
Every IC checked against its datasheet / layout guide / app note: `docs/design_review.md`.
Fixed: 5 V set point (LM66100 OR margin and copper drop), buck return-path vias, two firmware
back-powering faults on the sensor rail. Open items carried to REVIEW.md.

## 9. Stackup and signal integrity (atlc 4.6.1, 2D finite-difference field solver)
`sim/si/xsec.py` draws each cross-section from the stackup in the board file (5 µm per pixel,
grounded enclosure) and solves it.

| Structure | Result |
|---|---|
| USB D+/D− 0.25 / 0.15 mm on F.Cu over In1 | Zdiff 84.7 Ω with the GND pour, 86.8 Ω without (USB: 90 Ω ±15 %) |
| 0.127 mm signal, F.Cu | 67–73 Ω |
| 0.127 mm signal, In2 | 64–71 Ω |
| Coupling, 0.127 mm tracks, F.Cu | K = 0.33 / 0.19 / 0.11 / 0.05 at 0.10 / 0.20 / 0.30 / 0.50 mm gap |
| In2 over In3 broadside | K = 0.12 |

`sim/si/xtalk_scan.py` then walks every clock and fast-edge net on the routed board, sums parallel
coupled length to each neighbour and estimates near-end crosstalk with the saturating model:
worst case SD_CLK → CAN1_H, 15 mm at 0.14 mm gap, **1.1 % of swing**; every other pair < 1 %.

## 10. Power integrity (`sim/pi/ir_drop.py`, resistive mesh on the routed copper)
| Net | Load | Drop |
|---|---|---|
| VBAT_RAW (pads → FET) | 3 A | 56 mV |
| VBAT (FET → buck VIN) | 3 A | 20 mV |
| +5V (inductor → TPS2553s) | 1.3 A + 1.2 A | 235 / 167 mV (open item; covered by the 5.09 V set point) |
| +3V3 (inductor → MCU, SD) | 0.35 A | ≤ 46 mV |

## 11. Thermal (`sim/thermal/thermal.py`, board-level conduction + convection)
Still air (h = 12 W/m²K per face) and prop wash (50 W/m²K): board 37–86 °C, B360A case up to ~114 °C
at 6S / 2.5 A in still air. The IMU heater cannot hold a set point (see design_review.md).

## 12. Firmware build and CI
The board port builds at PX4 commit c0d2c54 on Linux (GCC 13.2, this repo's CI recipe) and macOS.
`.github/workflows/hardware.yml` runs ERC, DRC with parity, the pin-map check, KiBot (JLCPCB fab
package, schematic PDF, iBOM, STEP) and the PX4 build on every push; Simantic runs when a
`SIMANTIC_TOKEN` secret exists.

## 13. Not yet done
- Fab DFM: JLCPCB online DFM and a second fab's check on `fab/fc-h743-gerbers.zip` (need the owner's logins).
- Independent review (REVIEW.md).
- TI's own TPS54360B transient model (download needs the owner's OK) and a bench load step.
