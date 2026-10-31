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
562 vias, ~3 000 track segments, GND pours on all signal layers stitched to the In1/In4 planes.

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
Averaged current-mode model of the TPS54360B with the chosen compensation (9.09 kΩ / 4.7 nF / 47 pF),
27 corners (load 0.3–3.5 A, effective Cout 27–51 µF, sampling-pole Q 0.5–2): crossover 19–36 kHz, phase margin ≥ 66.4°,
gain margin ≥ 12.9 dB. 0.3 → 2.5 A step at 1 A/µs: ±6 % (`docs/power_sim.md`, `sim/buck/`).

## 7. PX4 on the netlist (Simantic 0.8.7, STM32H743VI model)
`sim/simantic/scenario.yaml` is generated from the netlist (`scripts/gen_scenario.py`): bus, chip select
and address of every sensor come from `design.py`, so a wiring or pin-map mistake makes the firmware miss
its sensor. Firmware: PX4 main (1.18.0-80) with the `dvntekim_fch743` board port in `firmware/`.

Result: **PASS, 5 expected strings present, 2 forbidden absent** (`docs/reports/simantic_console.txt`):
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

## 8. Not yet done
- JLCPCB online DFM on `fab/fc-h743-gerbers.zip` (needs the owner's JLCPCB login).
- Independent review (REVIEW.md).
