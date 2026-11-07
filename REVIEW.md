# Review checklist — fc-h743 rev B

Status: **DRAFT UNTIL INDEPENDENT REVIEW.** Tick each line with initials and date. Any "no" blocks ordering.

## 1. Schematic
- [ ] Power entry: DMP4013LFGQ reverse-polarity FET + BZT52C12 gate clamp; SMBJ28A TVS is *after* the FET (protects downstream, FET sees the surge). Check the FET's Vds and SOA against the battery's worst transient.
- [ ] TPS54360B: RT 162 kΩ → ~597 kHz; UVLO divider R5/R6 = 147k/36k gives start 5.9 V / stop 5.4 V typical (start 5.4–6.4 V over the EN threshold tolerance), fine for 2S–6S above ~3.2 V/cell; comp 9.09 kΩ / 4.7 nF / 47 pF matches `docs/power_sim.md`.
- [ ] 5 V set point: R8/R9 = 53.6k/10k → 5.09 V (raised from 4.98 V in rev-A-draft2 so the LM66100 OR prefers the buck over USB and the 5 V switches keep ≥ 4.75 V at their current limits). Load release peaks at 5.39 V in simulation; every part on +5V/+5V_FMU is rated 5.5 V.
- [ ] L1 FXL0530 saturates at 5 A, below the TPS54360B switch limit (5.5 A typ, 6.8 A max). Accept (3 A load; molded-powder cores saturate softly) or pick a ≥ 7 A part. Rev B search (2026-11-08): no 4.7 µH part in the 5.4 × 5.2 mm footprint above ~6.5 A on LCSC (Codaca CSHB0530R-4R7M, 6.5 A, is not stocked there); ≥ 7 A needs a 6.6 × 7 mm part and a buck re-layout.
- [ ] B360A catch diode current and reverse-voltage rating vs 6S + transients.
- [ ] LM66100 ideal-diode OR: USB path CE tied to +5V so the buck wins when present; no back-feed into USB.
- [ ] TPS2553 limits: PERIPH and CAN5V ILIM resistors give the intended trip current.
- [ ] STM32H743 VCAP1/VCAP2 (2.2 µF each), VDDA filter (FB1 + caps), VREF+, BOOT0 pull-down + solder jumper, NRST cap — per ST AN4938.
- [ ] HSE 16 MHz crystal, 12 pF load caps for CL = 9 pF (incl. ~3 pF stray); check the crystal's ESR against the H7 oscillator's gm_crit (AN2867).
- [ ] ICM-45686: CLKIN from PB10 (TIM2_CH3); AP_CS/INT; VDDIO from +3V3_SENS.
- [ ] BMI088: separate accel/gyro CS, PS pin strapping for SPI, SDO tri-stated correctly.
- [ ] BMP581: SDO strap gives address 0x47; INT pulled down; CSB high for I2C.
- [ ] TCAN1462V ×2: STB lines default to normal mode at boot? (PX4 drives low); split termination (60R+60R+4.7 nF) behind solder jumpers.
- [ ] microSD: 47k pull-ups on CMD/D0–D3, 22 Ω series R on CLK near the MCU. No card-detect is wired (as FMUv6C); PX4 finds the card at mount.
- [ ] USB-C: CC1/CC2 5.1 kΩ to GND, ESD array (U30), VBUS sense divider to PA9.
- [ ] Every connector pinout matches the device it plugs into (Pixhawk standard where noted on the schematic).

## 2. Pin map / firmware
- [ ] `docs/pinmap.md`: every alternate function is valid (script PASS) — spot-check 10 pins by hand in the STM32H743 datasheet (DS12110) AF table.
- [ ] `firmware/.../board_config.h`, `spi.cpp`, `i2c.cpp`, `timer_config.cpp` agree with the netlist (the Simantic scenario is generated from the netlist and must find every sensor).
- [ ] IMU rotation `-R 14` (roll 180°, yaw 270°) for both bottom-side IMUs (rev A had `-R 6`, which leaves Z inverted for a bottom-side part). Tilt test: board flat top-up → accel z ≈ −9.8; nose down → x < 0.
- [ ] Sensor-rail power cycle (rev-A-draft2 firmware fix): with PB2 low, PB10 and every SPI1/SPI2 pin read ≤ 0.3 V (no back-powering of the sensors).
- [ ] 32 kHz IMU clock: measure on PB10 with a scope. **The simulator showed 16 kHz** (it likely does not model the ×2 APB1 timer clock; the firmware follows RM0433). The ICM-45686 accepts 20–40 kHz only, so 16 kHz on hardware would be a failure: change ARR in `board_imu_clkin_start()`.
- [ ] PX4 parameters live on the SD card (`/fs/microsd/params`); no FRAM on this board. Decide whether that is acceptable (an SD-less boot loses params) or move to flash-based params (see `corvon/743v2` in PX4).

## 3. Layout
- [ ] Stackup in the board file = the one selected at JLCPCB (JLC06161H-3313D). If JLC only offers 3313A for 6 layers, In2/In3 sit 0.109 mm apart: re-check crosstalk on the SPI and SDMMC buses before accepting.
- [ ] Buck hot loop (C_in → TPS54360B VIN/SW → B360A → GND) as small as the TI layout example; nothing sensitive under the switch node or L1 on any layer.
- [ ] IMUs ≥ 10 mm from L1 / switch node (rev B layout: 18.4 mm).
- [ ] Crystal: short traces, GND guard, no signals under it on F.Cu/In2.
- [ ] USB pair routed together, no stubs; ESD array between connector and MCU.
- [ ] No copper or vias under the BMP581 vent; foam cover clearance.
- [ ] Thermal vias under TPS54360B PowerPAD into the GND planes.
- [ ] GND stitching: every isolated pour island has a via (DRC 0 unconnected).
- [ ] Mounting holes: no tracks within 1 mm of the 4 mm hole edge and no via closer than 1 mm (rev-A-draft3 removed 21 GND stitching vias that sat 0.37–0.92 mm away). Only GND copper sits inside 1.5 mm. Confirm against the frame's standoffs / grommets.
- [ ] Silkscreen: polarity and pin-1 marks visible after assembly (silk warnings in DRC are cosmetic overlaps; review the render).
- [ ] DRC report `docs/reports/drc.rpt`: 0 errors, 0 unconnected (59 silk warnings are cosmetic — check the render).
- [ ] VIN path: U1 pin 2 is fed by an F.Cu pour from three VBAT vias; part of VBAT runs at 0.4 mm on In2 (0.5 oz).
      Fine at 4S–6S (~1 A); widen before using 2S at full 5 V load (~2 A).
- [ ] BUCK_COMP is routed 13 mm (U1 pin 6 to R10/C15 on the left). Low-frequency node, but keep it away from SW in review.
- [ ] 16 via-in-pad (0.35/0.15 mm) on GND pads of IMU/VDDA/crystal caps: order epoxy-filled and capped vias.
- [ ] C8 (second 100 nF VIN cap) was dropped: C3 sits directly under the VIN vias and does that job, with a 1.5 mm track to U1's PowerPAD vias for its return. Confirm.
- [ ] Buck return path (rev-A-draft2): D3 anode has two vias, C11/C12 got GND vias, buck GND pads are solid to the pour. Check against the TPS54360B layout example.
- [ ] **Rev B IMU island** (docs/revB_thermal.md): two 1 mm milled slots, copper-free edge bridges, 2.2 mm corner bridge. Check the slots in the Gerber viewer and that the fab mills them (not V-cut); slot A sits 0.75 mm from the H2 hole edge.
- [ ] Heater: 2 × 12 Ω 2010 in series from +5V, 1.08 W, 0.54 W per 0.75 W part (72 %). Both on F.Cu of the island; AO3400A Q2 low side, gate R42 4.7 kΩ / R43 100 kΩ.
- [ ] TMP302A (U23) strapping: TRIPSET1 = VS, TRIPSET0 = GND → 60 °C; HYSTSET = VS → 10 °C; OUT open-drain on HEATER_G. Check against the TI strap table; check that 4.7 kΩ from PB9 cannot overpower OUT's sink current.
- [ ] Heater loop margin: the model holds ±0.55 °C at 51 °C only if the built island's isolation is ≥ 83 % of the modelled 36.7 K/W in prop wash. **First bench measurement on a built board.**
- [ ] BMI088 is unheated in rev B (no room on the island for its GND vias; Bosch forbids copper under it). Accept relying on PX4 thermal calibration for the secondary IMU.
- [ ] Four GND via-in-pad on the BMI088 (pads 2, 4, 6, 7), carried over from rev A: acceptable only with epoxy-filled, capped vias.
- [ ] Island copper: no GND pour islands (checked with `scripts/gnd_graph.py`); the ICM-45686 GND pad and caps reach In1/In4 through 0.35/0.15 mm vias.
- [ ] +5V to the TPS2553 switches runs ~60 mm around the MCU: 243 mV / 173 mV drop at their current limits in rev B (`sim/pi`; the heater now adds 0.21 A). Not rerouted in rev B: no free corridor without moving ~20 nets.
- [ ] B360A reaches ~114 °C case at 6S / 2.5 A in still air (rated 150 °C). Fine in flight (~76 °C); avoid long full-load bench runs on 6S without airflow.

## 4. Manufacturing (JLCPCB)
- [ ] CI (`.github/workflows/hardware.yml`) green on the commit being ordered: ERC, DRC + parity, pin map, KiBot fab package, PX4 build.
- [ ] Gerber zip passes JLCPCB's online DFM. JLCDFM run 2026-11-07 on rev-A-draft2: one real finding (vias near mounting holes) fixed in draft3; every other flag explained in docs/design_review.md. **Not yet run on rev B** (slot width, slot to hole, slot to copper). Re-run on the commit being ordered.
- [ ] Second fab's DFM (PCBWay) on the same zip.
- [ ] JLC quote settings: 6 layers, 1.6 mm, JLC06161H-3313D (Specify Stackup: Yes), ENIG, via covering epoxy-filled & capped, min via hole 0.15 mm; NPTH holes (4 × 4.0 mm, 2 × 0.65 mm) shown as non-plated in the order preview.
- [ ] 0.35/0.15 mm vias (if any are listed in the DRC report) are inside JLC's 6-layer capability and do not add cost.
- [ ] Every BOM line in stock on the day; extended-part fees accepted. Rev B lines: 12 Ω 2010 C3013299 (7,000 on 2026-11-08), TMP302A C2877557, 4.7 kΩ C25900.
- [ ] CPL rotations checked part by part in JLC's placement preview (KiCad and JLC disagree on several packages: SOT-23-6, VSON, LGA, USB-C).
- [ ] Bottom-side assembly quoted (standard PCBA, both sides).
- [ ] BMI088 / LGA parts: X-ray inspection option if JLC requires it.

## 5. Sign-off
| Reviewer | Date | Result |
|---|---|---|
| | | |
