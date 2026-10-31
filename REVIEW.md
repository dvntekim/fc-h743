# Review checklist — fc-h743 rev A

Status: **DRAFT UNTIL INDEPENDENT REVIEW.** Tick each line with initials and date. Any "no" blocks ordering.

## 1. Schematic
- [ ] Power entry: DMP4013LFGQ reverse-polarity FET + BZT52C12 gate clamp; SMBJ28A TVS is *after* the FET (protects downstream, FET sees the surge). Check the FET's Vds and SOA against the battery's worst transient.
- [ ] TPS54360B: RT 162 kΩ → ~597 kHz; UVLO divider (453k/36k) start/stop voltages match a 2S–6S pack; comp 9.09 kΩ / 4.7 nF / 47 pF matches `docs/power_sim.md`.
- [ ] B360A catch diode current and reverse-voltage rating vs 6S + transients.
- [ ] LM66100 ideal-diode OR: USB path CE tied to +5V so the buck wins when present; no back-feed into USB.
- [ ] TPS2553 limits: PERIPH and CAN5V ILIM resistors give the intended trip current.
- [ ] STM32H743 VCAP1/VCAP2 (2.2 µF each), VDDA filter (FB1 + caps), VREF+, BOOT0 pull-down + solder jumper, NRST cap — per ST AN4938.
- [ ] HSE 16 MHz crystal, 12 pF load caps for CL = 9 pF (incl. ~3 pF stray); check the crystal's ESR against the H7 oscillator's gm_crit (AN2867).
- [ ] ICM-45686: CLKIN from PB10 (TIM2_CH3); AP_CS/INT; VDDIO from +3V3_SENS.
- [ ] BMI088: separate accel/gyro CS, PS pin strapping for SPI, SDO tri-stated correctly.
- [ ] BMP581: SDO strap gives address 0x47; INT pulled down; CSB high for I2C.
- [ ] TCAN1462V ×2: STB lines default to normal mode at boot? (PX4 drives low); split termination (60R+60R+4.7 nF) behind solder jumpers.
- [ ] microSD: pull-ups on CMD/D0–D3, series R on CLK near the MCU, card-detect.
- [ ] USB-C: CC1/CC2 5.1 kΩ to GND, ESD array (U30), VBUS sense divider to PA9.
- [ ] Every connector pinout matches the device it plugs into (Pixhawk standard where noted on the schematic).

## 2. Pin map / firmware
- [ ] `docs/pinmap.md`: every alternate function is valid (script PASS) — spot-check 10 pins by hand in the STM32H743 datasheet (DS12110) AF table.
- [ ] `firmware/.../board_config.h`, `spi.cpp`, `i2c.cpp`, `timer_config.cpp` agree with the netlist (the Simantic scenario is generated from the netlist and must find every sensor).
- [ ] IMU rotation `-R 6` correct for the bottom-side mounting (check with a tilt test on the bench).
- [ ] 32 kHz IMU clock: measure on PB10 with a scope. **The simulator showed 16 kHz** (it may not model the ×2 APB1 timer clock); if hardware also shows 16 kHz, change ARR in `board_imu_clkin_start()`.
- [ ] PX4 parameters live on the SD card (`/fs/microsd/params`); no FRAM on this board. Decide whether that is acceptable (an SD-less boot loses params) or move to flash-based params (see `corvon/743v2` in PX4).

## 3. Layout
- [ ] Stackup in the board file = the one selected at JLCPCB (JLC06161H-3313D). If JLC only offers 3313A for 6 layers, In2/In3 sit 0.109 mm apart: re-check crosstalk on the SPI and SDMMC buses before accepting.
- [ ] Buck hot loop (C_in → TPS54360B VIN/SW → B360A → GND) as small as the TI layout example; nothing sensitive under the switch node or L1 on any layer.
- [ ] IMUs ≥ 10 mm from L1 / switch node (layout: ~15 mm).
- [ ] Crystal: short traces, GND guard, no signals under it on F.Cu/In2.
- [ ] USB pair routed together, no stubs; ESD array between connector and MCU.
- [ ] No copper or vias under the BMP581 vent; foam cover clearance.
- [ ] Thermal vias under TPS54360B PowerPAD into the GND planes.
- [ ] GND stitching: every isolated pour island has a via (DRC 0 unconnected).
- [ ] Mounting-hole keepouts respected (M3 + nylon hardware, 3 mm keepout).
- [ ] Silkscreen: polarity and pin-1 marks visible after assembly (silk warnings in DRC are cosmetic overlaps; review the render).
- [ ] DRC report `docs/reports/drc.rpt`: 0 errors, 0 unconnected (61 silk warnings are cosmetic — check the render).
- [ ] VIN path: U1 pin 2 is fed by an F.Cu pour from three VBAT vias; part of VBAT runs at 0.4 mm on In2 (0.5 oz).
      Fine at 4S–6S (~1 A); widen before using 2S at full 5 V load (~2 A).
- [ ] BUCK_COMP is routed 13 mm (U1 pin 6 to R10/C15 on the left). Low-frequency node, but keep it away from SW in review.
- [ ] 17 via-in-pad (0.35/0.15 mm) on GND pads of IMU/VDDA/crystal caps: order epoxy-filled and capped vias.
- [ ] C8 (second 100 nF VIN cap) was dropped: C3 sits directly under the VIN vias and does that job. Confirm.
- [ ] IMU heater: 4 × 120 Ω 1206 from +5V (≈ 0.83 W total); check the 1206 rating and the AO3400A drive from PB9.

## 4. Manufacturing (JLCPCB)
- [ ] Gerber zip passes JLCPCB's online DFM (upload `fab/fc-h743-gerbers.zip`).
- [ ] 0.35/0.15 mm vias (if any are listed in the DRC report) are inside JLC's 6-layer capability and do not add cost.
- [ ] Every BOM line in stock on the day; extended-part fees accepted.
- [ ] CPL rotations checked part by part in JLC's placement preview (KiCad and JLC disagree on several packages: SOT-23-6, VSON, LGA, USB-C).
- [ ] Bottom-side assembly quoted (standard PCBA, both sides).
- [ ] BMI088 / LGA parts: X-ray inspection option if JLC requires it.

## 5. Sign-off
| Reviewer | Date | Result |
|---|---|---|
| | | |
