# Design review against vendor documents: fc-h743 rev A

Status: **DRAFT until independent review.** This is the author's own check of each IC against
its datasheet, layout guide or app note. It does not replace a second engineer (REVIEW.md).

Legend: **OK** meets the vendor guidance · **FIXED** failed and was changed in rev-A-draft2 ·
**NOTE** acceptable with a stated limit · **OPEN** carried to REVIEW.md / rev B.

## Power

### TPS54360B 5 V buck (TI datasheet)
| Check | Vendor guidance | Board | Result |
|---|---|---|---|
| Switching frequency | R_T = 101756 x f^-1.008 (kOhm, kHz) | 162 kOhm -> 597 kHz | OK |
| Minimum on-time | 135 ns typ | 340 ns at 25.2 V in, 5.09 V out | OK |
| UVLO | EN 1.2 V (1.1-1.3), I_P 1.2 uA, I_HYS 3.4 uA | 147 k / 36 k: start 5.9 V, stop 5.4 V (typ); start spreads 5.4-6.4 V over EN tolerance | NOTE: a 2S pack below ~3.2 V/cell may not start at the worst-case threshold |
| Boot capacitor | 0.1 uF X5R/X7R >= 10 V | 100 nF X7R 16 V, loop 2.3 mm | OK |
| Input capacitance | >= 3 uF effective, rated above V_IN max | 2 x 10 uF 50 V 0805 + 100 nF 50 V; >= 6 uF effective at 25 V | OK |
| Inductor ripple | > 150 mA for stable PWM; K_IND ~0.3 | 1.43 A p-p at 25.2 V, 0.58 A p-p at 7.4 V | OK |
| Inductor saturation | most conservative: I_sat >= switch current limit (5.5 A typ, 6.8 A max) | FXL0530 I_sat 5 A | OPEN: fine for the 3 A load, but a hard short can saturate L1 before the limit trips. Rev B: 6 x 6 mm part with I_sat >= 7 A |
| Catch diode | V_R >= V_IN max (60 V preferred), I_F above peak inductor current | B360A 60 V 3 A | OK rating; thermal see below |
| Output set point | V_out = 0.8 x (1 + R_top/R_bot) | 53.6 k / 10 k -> 5.09 V | FIXED (was 4.98 V; see LM66100 and IR drop) |
| Loop | crossover < f_sw/10; PM > 45 deg | 19-35 kHz, PM >= 66.6 deg, GM >= 13.1 dB (27 corners, `sim/buck`) | OK |
| Layout: RT, FB, COMP near IC | short traces, RT close | pad-to-pad 2.8 / 3.3-3.7 / 5.0-5.4 mm | OK |
| Layout: PowerPAD | multiple vias to internal GND planes | thermal-via footprint, In1/In4 GND | OK |
| Layout: hot loop | C_in - VIN - diode anode loop small | diode anode had 1 via, output caps C11/C12 had none, pads on thermal spokes | FIXED: added vias, solid pad connections; return runs on In1 0.18 mm below F.Cu |
| Layout: SW node | minimal copper, near SW pins | 26 mm2 pour with keep-out, nothing crosses it | OK |

### LM66100 ideal-diode OR (TI datasheet)
| Check | Vendor guidance | Board | Result |
|---|---|---|---|
| Pinout (DCK) | 1 VIN, 2 GND, 3 CE, 4 NC, 5 ST, 6 VOUT | same | OK |
| ORing | CE of each device to the opposite source | U3 CE to +5V (buck); U2 CE to GND (always on, buck side) | OK |
| Turn-off | CE above VIN by 0-80 mV turns the device off | buck was 4.98 V vs USB up to 5.25 V: USB path could stay on | FIXED: buck now 5.09 V; USB above 5.09 V still shares the FMU load, harmless |
| ST pin | open drain, low when disabled, Hi-Z when enabled | 10 k pull-up: high = running from USB | OK |
| Current | 1.5 A continuous | +5V_FMU load ~0.5 A | OK |
| VIN range | 1.5-5.5 V recommended, 6 V abs max | 5.09 V, 5.39 V peak on load release | OK |

### TLV62569 3V3, LP5907 sensor LDO, TPS2553 switches
| Part | Check | Result |
|---|---|---|
| TLV62569 | pinout, FB 453 k / 100 k = 3.32 V, 2.2 uH, 2 x 10 uF out, 10 uF in | OK |
| LP5907 | pinout, 1 uF in and out, EN pulled up (sensors on by default) | OK |
| TPS2553 | EN active high, I_LIM = 23850 / R^0.977: 20 k -> 1.28 A, 22 k -> 1.17 A | OK |

### Reverse polarity and surge
| Check | Result |
|---|---|
| DMP4013 P-FET: drain to battery, source to load, gate pulled to GND, 12 V zener clamps Vgs | OK |
| SMBJ28A after the FET: 28 V stand-off above 6S (25.2 V); clamp ~45 V below TPS54360B 60 V rating | OK |

## MCU: STM32H743VIT6 (DS12110, AN4938, AN2867)
| Check | Board | Result |
|---|---|---|
| VDD decoupling | 5 VDD pins x 100 nF + 4.7 uF bulk, VBAT 100 nF | OK |
| VCAP | 2 x 2.2 uF | OK |
| VDDA | ferrite + 1 uF + 100 nF | OK |
| VREF+ | tied to VDDA, 100 nF | NOTE: AN4938 shows 1 uF + 100 nF on VREF+; the shared 1 uF on VDDA is 3 mm away. Reviewer to confirm |
| BOOT0 / NRST | 10 k pull-down + DFU solder jumper / 100 nF | OK |
| HSE (AN2867) | X322516MLB4SI ESR 50 ohm, CL 9 pF -> gm_crit ~0.25 mA/V against the H7 limit of 1.5 mA/V (6x margin); 12 pF load caps | OK |

## Sensors
| Part | Check | Result |
|---|---|---|
| ICM-45686 (TDK DS-000577) | pinout matches the datasheet; reserved pins 2, 3, 7, 10, 11 may be left open | OK |
| ICM-45686 CLKIN | 20-40 kHz accepted on pin 9; firmware gives 240 MHz / 7500 = 32.000 kHz | OK; the simulator measured 16 kHz (model gap, timer clock); scope it at bring-up |
| BMP581 (Bosch DS004) | CSB hard-wired to VDDIO for I2C; SDO high -> 0x47 (must not float) | OK |
| BMP581 / all sensors | "holding any interface pin high while VDDIO is off can damage the device" | FIXED in firmware: SPI2 pins now parked during the rail power-cycle, 32 kHz clock started after it and stopped before `board_peripheral_reset()` cuts the rail. All pull-ups are on +3V3_SENS |
| BMI088 | PS = GND (SPI), separate accel / gyro CS, both SDO to MISO | OK (pin table not re-fetched this round) |

## Interfaces
| Part | Check | Result |
|---|---|---|
| USB-C | 5.1 k Rd on CC1/CC2, shield 1 M // 4.7 nF | OK |
| USBLC6-2SC6 | flow-through pinout 1/6 and 3/4, VBUS on pin 5 | OK |
| USB D+/D- | 90 ohm +-15 % differential | atlc: 84.7 ohm (with GND pour), 86.8 ohm (without) | OK |
| microSD | 47 k pull-ups on CMD/D0-D3 (SD spec 10-100 k), 22 ohm on CLK; no card-detect wired | OK; REVIEW.md corrected (it listed a card-detect) |
| TCAN1462V | VCC 4.5-5.5 V from +5V_FMU (~5.05 V), VIO 3.3 V, STB driven low at boot by PX4 | OK |

## Thermal (`sim/thermal`)
| Case | Board max | IMUs | B360A case |
|---|---|---|---|
| 6S, 2.5 A out, still air | 86 C | 75 C | ~114 C (rated 150 C) |
| 4S, 1.2 A out, still air | 57 C | 53 C | 68 C |
| 4S, 1.2 A + heater full on, still air | 72 C | 71 C | 83 C |
| 6S, 2.5 A out, prop wash | 49 C | 39 C | 76 C |
| 4S, 1.2 A + heater, prop wash | 41 C | 40 C | 52 C |

**OPEN: the IMU heater cannot regulate.** The 0.86 W heater warms the whole copper-heavy board, so
it lifts the IMUs by ~18 C in still air and ~7 C in prop wash. On the bench the board alone is
above the 45 C set point; in flight at 25 C ambient the set point is out of reach. Rev A relies on
PX4's thermal calibration (TC_*). Rev B: isolate the IMU island with routed slots and a narrow
neck so the heater warms only the IMUs.

## Power integrity (`sim/pi`) at worst-case currents
| Net | Load | Drop | Result |
|---|---|---|---|
| VBAT_RAW, pads -> FET | 3 A | 56 mV | NOTE: one 13 mm hop on 0.5 oz In2 |
| VBAT, FET -> buck VIN | 3 A | 20 mV | OK |
| +5V, inductor -> TPS2553 switches | 1.3 A + 1.2 A (their limits) | 235 / 167 mV | OPEN: ~60 mm route; with the 5.09 V set point the switch outputs stay >= ~4.75 V at their limits. Rev B: direct trunk |
| +3V3, inductor -> MCU / SD | 0.35 A | <= 46 mV | OK |

## Signal integrity (`sim/si`)
| Check | Result |
|---|---|
| Single-ended 0.127 mm: F.Cu 67-73 ohm, In2 64-71 ohm | OK for SPI / SDMMC at these lengths |
| Coupling 0.127 mm tracks: K = 0.33 at 0.10 mm gap, 0.19 at 0.20 mm, 0.05 at 0.50 mm (F.Cu); In2/In3 broadside K = 0.12 | — |
| Crosstalk scan of every clock net on the routed board | worst SD_CLK -> CAN1_H 1.1 % of swing (15 mm at 0.14 mm); all others < 1 % | OK |

## Fab DFM: JLCDFM (JLCPCB's online DFM), 2026-11-07
Gerber zip of rev-A-draft2 uploaded through the JLCPCB quote page: detected as 6 layers, 50 × 50 mm,
via-in-pad (POFV) supported; all 13 layers and both drill files recognised.

| JLCDFM check | Danger / warning | What it is | Result |
|---|---|---|---|
| Via to PTH spacing | 2 / 0 | GND stitching vias 0.37 mm from the edge of the 4 mm mounting holes | **FIXED** (rev-A-draft3): 21 stitching vias within 1 mm of a mounting-hole edge removed; DRC 0/0/0, no GND islands |
| Annular ring | 19 / 81 | 0.35/0.15 mm vias (0.10 mm ring) and 0.45/0.20 mm vias (0.125 mm ring) | OK against JLC's multilayer rule (via diameter ≥ hole + 0.10 mm). The 0.15 mm drill puts the board in JLC's higher-cost via tier: select "Min via hole 0.15 mm" on the quote |
| Via to pad / pad spacing | 5 / 2, 9 / 87 | every hit is a via touching or near its own pad, same net (checked from the board file) | OK with JLC's default epoxy-filled, capped vias on 6-layer boards |
| Slot width | 4 / 0 | USB-C shell slots, 0.6 mm | OK: JLC multilayer plated slot minimum is 0.35 mm |
| Trace spacing, THT to SMD, mask opening exposing trace | 1, 2, 1 | spacings at or above the 0.10 mm DRC rule; same-net pad exits | OK; DRC enforces 0.10 mm to other nets |
| Silkscreen to pad / hole | 100 / 0 each | silk touching pads and via holes (the 61 DRC silk warnings) | Cosmetic: the fab clips silk off pads and holes |
| Drill layers | — | JLCDFM's viewer labels both drill files "plated"; the NPTH file's header says `FileFunction,NonPlated` | Check NPTH holes in JLC's order preview |
