# fc-h743 — STM32H743 flight controller for a GPS-denied learned-control quadrotor

> **DRAFT UNTIL INDEPENDENT REVIEW.** Not yet reviewed by a second engineer and not ordered.
> Work through [REVIEW.md](REVIEW.md) before anyone pays for boards.

**View it in the browser (no install):**
- PCB: <https://kicanvas.org/?github=https://github.com/dvntekim/fc-h743/blob/main/kicad/fc.kicad_pcb>
- Schematic: <https://kicanvas.org/?github=https://github.com/dvntekim/fc-h743/blob/main/kicad/fc.kicad_sch>
- PDF schematic: [docs/schematic.pdf](docs/schematic.pdf)

| Top | Bottom |
|---|---|
| ![top](docs/render_top.png) | ![bottom](docs/render_bottom.png) |

## What it is

A 50 × 50 mm, 6-layer flight controller (30.5 mm M3 mount) that runs PX4 on an STM32H743VIT6.
It is adapted from the Pixhawk FMUv6C reference design (same MCU family, LQFP-100, same PX4 pin
roles where possible) and built for indoor, GPS-denied flight with a learned (RAPTOR-style)
controller, so the electrical effort goes into clean sensing, timing and telemetry:

| Area | What is on the board | Why |
|---|---|---|
| Primary IMU | TDK ICM-45686 on SPI1, **clocked by a 32 kHz reference from TIM2_CH3 (PB10)** | Locks the IMU's ODR to the MCU clock: no sample-rate drift between IMU and controller. PX4 `icm45686 -C 32000` |
| Second IMU | Bosch BMI088 on its own bus (SPI2) | Vibration-robust accel; independent bus so one faulty sensor cannot stall the other |
| IMU thermal control | 4 × 120 Ω heater ring around both IMUs, AO3400A on PB9 | Holds the IMUs at 45 °C so bias does not drift with ambient (PX4 `HEATER1_TEMP`) |
| Barometer | Bosch BMP581 on I2C4 (0x47) | Lowest-noise MEMS baro in the class |
| CAN | 2 × TI TCAN1462V, CAN FD with signal improvement (8 Mbit/s) | DroneCAN/Cyphal sensors (flow, range) at FD rates |
| Motor outputs | 4 × bidirectional DShot on TIM1 + ESC serial telemetry (UART8) | RPM feedback for motor-aware learned control |
| Camera trigger | M7/M8 on TIM5 (capture/trigger) | Hardware timestamps for visual odometry |
| Power | TPS54360B 5 V buck (60 V in, switch node as a 26 mm² pour, boot loop 2.3 mm), ideal-diode OR with USB (2 × LM66100), TLV62569 3V3, LP5907 sensor LDO, 2 × TPS2553 current-limited switches | Sensor rail can be power-cycled from firmware (PB2) to recover a hung sensor |
| Storage / USB | microSD on SDMMC2 (4-bit), USB-C (FS) | Logs and parameters; PX4 console |

## Verification status

| Check | Tool | Result |
|---|---|---|
| Electrical rules | KiCad 9 ERC | **0 errors, 0 warnings** |
| Design rules | KiCad 9 DRC (JLCPCB 6-layer limits, `kicad/fc.kicad_dru`) | **0 errors, 0 unconnected** (61 silkscreen-cosmetic warnings) |
| Schematic ↔ PCB parity | KiCad 9 DRC `--schematic-parity` | 0 issues |
| Pin map | `scripts/pinmap_check.py` against ST's pin data (KiCad STM32H743VITx symbol) | **PASS**, 74 pins — [docs/pinmap.md](docs/pinmap.md) |
| BOM availability | JLCPCB parts API | 69/69 parts in stock on 2026-10-31 — [docs/bom_check.md](docs/bom_check.md) |
| 5 V buck loop | ngspice averaged current-mode model | crossover 19–36 kHz, phase margin ≥ 66°, gain margin ≥ 12.9 dB over load/C/Q corners; 0.25→2.45 A step ±6 % — [docs/power_sim.md](docs/power_sim.md) |
| Firmware on the netlist | PX4 board port + Simantic STM32H743 simulator, scenario generated from the netlist | **PASS**: ICM-45686 on SPI1, BMI088 on SPI2, BMP581 on I2C4 @0x47, CAN1 RX, SD logger, NSH — [docs/verification.md](docs/verification.md) |
| Manufacturability | JLCPCB online DFM on the Gerber zip | pending (needs the owner's JLCPCB login) |
| Independent review | second engineer | **not done** |

## Board

- **Stackup:** JLCPCB JLC06161H-3313D, 1.6 mm, ENIG (layer thicknesses checked against jlcpcb.com/impedance).
  F.Cu signal · In1 GND · In2 signal · In3 signal · In4 GND · B.Cu signal.
  Every signal layer sits 0.18–0.25 mm from its own GND plane; In2/In3 face each other across
  0.545 mm. Written into the board file (`Board Setup → Physical Stackup`).
- **USB D+/D−:** 0.25 mm / 0.15 mm gap on F.Cu over In1 ≈ 90 Ω differential (IPC-2141 estimate;
  confirm with JLCPCB's impedance calculator). USB FS is forgiving at this length.
- **Net classes:** HighCurrent (VBAT, switch node) 0.8 mm · Power 0.4 mm · Supply (3V3, VDDA) 0.3 mm ·
  signals 0.127 mm / 0.1 mm clearance · vias 0.45/0.2 mm, plus 20 at 0.35/0.15 mm of which 17 are via-in-pad
  (order with epoxy-filled, capped vias — JLC includes this on 6-layer boards; confirm on the quote).
- **Parts on both sides.** IMUs sit on the bottom inside the MCU's pin ring so their SPI runs are a few mm.
  Expected PX4 rotation `-R 6` (yaw 270°) — verify on the bench (REVIEW.md).

## Deviations from the spec doc (on purpose)

| Spec | Built | Reason |
|---|---|---|
| ≤ 38 × 38 mm | 50 × 50 mm | Courtyards alone filled 94 % of 38 × 38 with the frontier feature set (2 CAN FD, heater, two IMU buses, ideal-diode power path) |
| 4-layer | 6-layer | Two inner routing layers each next to a solid GND plane; needed to route LQFP-100 + both IMU buses at 50 × 50 |
| Top-side parts only | Both sides | IMUs under the MCU (short SPI, centroid placement); costs standard (not economic) assembly at JLCPCB |
| JLC04161H-3313 | JLC06161H-3313D | Follows from 6 layers |

## Repository

```
kicad/      KiCad 9 project (schematic, PCB, project library, DRC rules)
fab/        Gerber + drill zip, JLCPCB BOM and CPL, STEP
docs/       schematic PDF, renders, layer plots, pin map, critical nets, power sim, verification log, BOM check, reports/
firmware/   PX4 board port: boards/dvntekim/fch743
sim/        Simantic scenario + sensor peers (generated from the netlist); ngspice buck models
scripts/    everything above is generated from these (design.py is the single source of truth)
REVIEW.md   checklist for the independent reviewer and for bring-up
```

How it was made: `scripts/design.py` (parts, nets, pin map) → `gen_lib.py` → `gen_sch.py` (schematic, ERC) →
`gen_pcb.py` (placement) → `prep_route.py` → Freerouting 1.9 → `import_ses.py`, then finishing passes
(`fix_route.py` local router, `stitch.py`/`island_fix.py` GND stitching, `rework_power.py`, `sw_zone.py`,
`vin_zone.py`) → `drc.sh` → `export.sh`. The schematic regenerates from `design.py`; after the hand-finishing,
**`kicad/fc.kicad_pcb` is the source of truth for the layout** (re-running `gen_pcb.py` starts a new layout).

## Ordering

Do not order until REVIEW.md is signed off. Then upload `fab/fc-h743-gerbers.zip` to JLCPCB
(6 layers, 1.6 mm, JLC06161H-3313D, ENIG), add assembly with `fab/bom_jlc.csv` and `fab/cpl_jlc.csv`,
and check every rotation in the placement preview.
