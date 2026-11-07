"""Flight controller design: every part, its JLCPCB number, and every pin's net.

Single source of truth for the schematic generator, the pin-map check, the PX4
board port and the Simantic scenario. Pin map follows PX4's FMUv6C
(boards/px4/fmu-v6c, STM32H743VIT6 LQFP-100) wherever this board has the same
function; deviations are listed in PINMAP_NOTES.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = []

SHEETS = [
    ("power", "Power"),
    ("mcu", "MCU"),
    ("sensors", "Sensors"),
    ("storage_usb", "Storage + USB"),
    ("can", "CAN"),
    ("connectors", "Connectors"),
]

# Rails drawn as power symbols (global by definition)
RAILS = ["GND", "VBAT_RAW", "VBAT", "+5V", "+5V_FMU", "+5V_PERIPH", "+5V_CAN",
         "+3V3", "+3V3_SENS", "VDDA", "USB_VBUS", "USB_VBUS_F"]


GROUP = ["misc"]


def group(name):
    """Functional block the following parts belong to (drawn as a framed block on the sheet)."""
    GROUP[0] = name


def part(ref, lib, value, fp, lcsc, sheet, pins, **kw):
    p = dict(ref=ref, lib=lib, value=value, fp=fp, lcsc=lcsc, sheet=sheet, group=GROUP[0],
             pins={str(k): v for k, v in pins.items()})
    p.update(kw)
    PARTS.append(p)
    return p


# ---------- common passives (JLCPCB basic parts where possible) ----------
R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
R1206 = "Resistor_SMD:R_1206_3216Metric"

RES_LCSC = {  # 0402 1% thick film
    "22": "C25092", "33": "C25105", "47": "C25118", "60.4": "C60310", "100": "C25076",
    "1k": "C11702", "470": "C25117", "2k": "C4109", "2.2k": "C25879", "5.1k": "C25905",
    "10k": "C25744", "20k": "C25765", "22k": "C25768", "33k": "C25779",
    "36k": "C43676", "47k": "C25792", "52.3k": "C26982", "53.6k": "C53398", "100k": "C25741",
    "147k": "C64171", "162k": "C54068", "453k": "C27009", "1M": "C26083", "9.09k": "C11549",
    "6.04k": "C25981",
}
CAP = {  # value -> (footprint, lcsc, voltage note)
    "10pF": (C0402, "C32949", "50V C0G"), "33pF": (C0402, "C1562", "50V C0G"), "12pF": (C0402, "C1547", "50V C0G"),
    "47pF": (C0402, "C1567", "50V C0G"), "4.7nF": (C0402, "C1538", "50V X7R"),
    "100nF": (C0402, "C1525", "16V X7R"), "100nF/50V": (C0603, "C14663", "50V X7R"),
    "1uF": (C0402, "C52923", "25V X5R"), "2.2uF": (C0402, "C12530", "10V X5R"),
    "4.7uF": (C0603, "C19666", "25V X5R"), "10uF": (C0603, "C19702", "10V X5R"),
    "10uF/50V": (C0805, "C440198", "50V X5R"), "22uF": (C0805, "C45783", "25V X5R"),
}
_n = {}


def nref(prefix):
    _n[prefix] = _n.get(prefix, 0) + 1
    return f"{prefix}{_n[prefix]}"


def R(val, a, b, sheet, note=None, fp=R0402, lcsc=None):
    return part(nref("R"), "Device:R", val, fp, lcsc or RES_LCSC[val], sheet, {1: a, 2: b}, note=note)


def C(val, a, b, sheet, note=None):
    fp, lcsc, rating = CAP[val]
    return part(nref("C"), "Device:C", val.split("/")[0], fp, lcsc, sheet, {1: a, 2: b},
                note=note, rating=rating)


# ======================= POWER =======================
S = "power"
group("Battery input, reverse-polarity and surge protection")
part("J1", "Connector_Generic:Conn_01x02", "BATT PADS", "fc_custom:PowerPads_2x_3x5mm", "", S,
     {1: "VBAT_RAW", 2: "GND"}, note="2S-6S battery solder pads")
part("Q1", "fc_custom:DMP4013LFGQ", "DMP4013LFGQ-13", "Package_SON:Diodes_PowerDI3333-8", "C7264680", S,
     {1: "VBAT", 2: "VBAT", 3: "VBAT", 4: "RPP_G", 5: "VBAT_RAW"},
     note="Reverse-polarity P-FET: drain to input, source to load")
R("100k", "RPP_G", "GND", S, note="RPP gate pull-down")
part("D1", "Device:D_Zener", "BZT52C12", "Diode_SMD:D_SOD-123", "C43491", S,
     {1: "VBAT", 2: "RPP_G"}, note="Clamps Q1 Vgs to -12 V")
part("D2", "Device:D_Zener", "SMBJ28A", "Diode_SMD:D_SMB", "C113997", S,
     {1: "VBAT", 2: "GND"}, note="Unidirectional TVS, 28 V standoff, after RPP so reverse battery cannot forward-bias it")
C("10uF/50V", "VBAT", "GND", S)
C("10uF/50V", "VBAT", "GND", S)
C("100nF/50V", "VBAT", "GND", S, note="buck input HF, under the U1 VIN vias")
group("Battery voltage and ESC current sensing")
R("100k", "VBAT", "VBAT_SENSE", S, note="VBAT divider 11:1 -> 36 V full scale")
R("10k", "VBAT_SENSE", "GND", S)
C("100nF", "VBAT_SENSE", "GND", S)
R("1k", "ESC_CURR", "BATT_CURR_SENSE", S, note="ESC current RC filter, fc = 1.6 kHz")
C("100nF", "BATT_CURR_SENSE", "GND", S)

group("5 V buck: TPS54360B, 3.5 A, 597 kHz")
# 5 V main buck: TPS54360B, 600 kHz, 4.7 uH, peak-current mode
part("U1", "Regulator_Switching:TPS54360DDA", "TPS54360BDDAR", "Package_SO:TI_SO-PowerPAD-8_ThermalVias",
     "C524806", S, {2: "VBAT", 3: "BUCK_EN", 4: "BUCK_RT", 5: "BUCK_FB", 6: "BUCK_COMP",
                    7: "GND", 9: "GND", 8: "BUCK_SW", 1: "BUCK_BOOT"})
C("10uF/50V", "VBAT", "GND", S, note="buck input, at U1 VIN")
C("10uF/50V", "VBAT", "GND", S, note="buck input, at U1 VIN")
nref("C")  # C8 removed in layout rev: C3 (bottom, under the VIN vias) is the HF input cap
C("100nF", "BUCK_BOOT", "BUCK_SW", S)
R("147k", "VBAT", "BUCK_EN", S, note="UVLO divider, 0.5 V hysteresis")
R("36k", "BUCK_EN", "GND", S, note="UVLO start 5.9 V, stop 5.4 V")
R("162k", "BUCK_RT", "GND", S, note="fsw = 597 kHz")
part("D3", "Device:D_Schottky", "B360A-13-F", "Diode_SMD:D_SMA", "C94193", S,
     {1: "BUCK_SW", 2: "GND"}, note="60 V 3 A catch diode")
part("L1", "Device:L", "4.7uH", "Inductor_SMD:L_Changjiang_FXL0530", "C177246", S,
     {1: "BUCK_SW", 2: "+5V"}, note="FXL0530-4R7-M, Isat 5 A, 60 mOhm")
C("22uF", "+5V", "GND", S)
C("22uF", "+5V", "GND", S)
C("22uF", "+5V", "GND", S)
C("100nF", "+5V", "GND", S)
R("53.6k", "+5V", "BUCK_FB", S, note="Vout = 0.8 V x (1 + 53.6k/10k) = 5.09 V: above typical USB VBUS so the LM66100 OR prefers the buck, headroom for copper drop to the 5 V switches, load-release peak < 5.5 V")
R("10k", "BUCK_FB", "GND", S)
R("9.09k", "BUCK_COMP", "BUCK_CZ", S, note="Type II comp, fc ~ 40 kHz (see sim/buck)")
C("4.7nF", "BUCK_CZ", "GND", S)
C("47pF", "BUCK_COMP", "GND", S)

group("+5V_FMU: ideal-diode OR, buck has priority over USB")
# 5V_FMU: ideal-diode OR of buck and USB, buck has priority
part("U2", "fc_custom:LM66100", "LM66100DCKR", "Package_TO_SOT_SMD:SOT-363_SC-70-6", "C2869734", S,
     {1: "+5V", 2: "GND", 3: "GND", 4: None, 5: "MAIN_ST", 6: "+5V_FMU"}, note="main path, always enabled")
R("100k", "MAIN_ST", "GND", S, note="U2 status unused; datasheet allows GND")
part("F1", "Device:Polyfuse", "0.5A", "Fuse:Fuse_1206_3216Metric", "C69688", S,
     {1: "USB_VBUS", 2: "USB_VBUS_F"}, note="nSMD050")
part("U3", "fc_custom:LM66100", "LM66100DCKR", "Package_TO_SOT_SMD:SOT-363_SC-70-6", "C2869734", S,
     {1: "USB_VBUS_F", 2: "GND", 3: "+5V", 4: None, 5: "USB_PWR_SEL", 6: "+5V_FMU"},
     note="USB path; CE tied to +5V so the buck wins whenever it is up")
R("10k", "USB_PWR_SEL", "+3V3", S, note="ST high = board running from USB")
C("10uF", "+5V_FMU", "GND", S)
C("100nF", "+5V_FMU", "GND", S)
R("10k", "+5V", "MAIN_5V_DET", S, note="buck-present detect for PX4 (PA15)")
R("10k", "MAIN_5V_DET", "GND", S)
R("10k", "+5V_FMU", "V5_SENSE", S, note="scaled 5 V for PX4 ADC (PA4), /2")
R("10k", "V5_SENSE", "GND", S)
C("100nF", "V5_SENSE", "GND", S)

group("+3V3: TLV62569 2 A buck")
# 3V3 for MCU/SD/CAN logic: TLV62569 2 A sync buck
part("U4", "Regulator_Switching:TLV62569DBV", "TLV62569DBVR", "Package_TO_SOT_SMD:SOT-23-5", "C141836", S,
     {4: "+5V_FMU", 1: "+5V_FMU", 2: "GND", 3: "SW_3V3", 5: "FB_3V3"})
C("10uF", "+5V_FMU", "GND", S, note="U4 input")
part("L2", "Device:L", "2.2uH", "Inductor_SMD:L_1008_2520Metric", "C98350", S,
     {1: "SW_3V3", 2: "+3V3"}, note="WPN252012H2R2MT, Isat 3 A")
R("453k", "+3V3", "FB_3V3", S, note="Vout = 0.6 V x (1 + 453k/100k) = 3.32 V")
R("100k", "FB_3V3", "GND", S)
C("10pF", "+3V3", "FB_3V3", S, note="feed-forward")
C("10uF", "+3V3", "GND", S)
C("10uF", "+3V3", "GND", S)

group("+3V3_SENS: low-noise LDO, MCU-switchable")
# 3V3_SENS: low-noise LDO, MCU can power-cycle the sensors
part("U5", "Regulator_Linear:LP5907MFX-3.3", "LP5907MFX-3.3/NOPB", "Package_TO_SOT_SMD:SOT-23-5", "C80670", S,
     {1: "+5V_FMU", 3: "SENS_EN", 2: "GND", 4: None, 5: "+3V3_SENS"}, note="6.5 uVrms")
C("1uF", "+5V_FMU", "GND", S, note="U5 input")
C("1uF", "+3V3_SENS", "GND", S, note="U5 output")
R("100k", "SENS_EN", "+3V3", S, note="sensors on by default; PX4 can cycle them")

group("Current-limited peripheral power")
# Current-limited peripheral power (Pixhawk practice)
part("U6", "fc_custom:TPS2553", "TPS2553DBVR", "Package_TO_SOT_SMD:SOT-23-6", "C55266", S,
     {1: "+5V", 2: "GND", 3: "PERIPH_EN", 4: "PERIPH_nOC", 5: "PERIPH_ILIM", 6: "+5V_PERIPH"},
     note="TELEM1/2, GPS, RC, AUX")
R("20k", "PERIPH_ILIM", "GND", S, note="limit 1.20-1.38 A")
R("100k", "PERIPH_EN", "+3V3", S)
R("10k", "PERIPH_nOC", "+3V3", S)
C("100nF", "+5V", "GND", S, note="U6 input")
C("22uF", "+5V_PERIPH", "GND", S)
part("U7", "fc_custom:TPS2553", "TPS2553DBVR", "Package_TO_SOT_SMD:SOT-23-6", "C55266", S,
     {1: "+5V", 2: "GND", 3: "CAN5V_EN", 4: "CAN5V_nOC", 5: "CAN5V_ILIM", 6: "+5V_CAN"},
     note="CAN1/CAN2 connector power")
R("22k", "CAN5V_ILIM", "GND", S, note="limit 1.09-1.26 A")
R("100k", "CAN5V_EN", "+3V3", S)
R("10k", "CAN5V_nOC", "+3V3", S)
C("100nF", "+5V", "GND", S, note="U7 input")
C("10uF", "+5V_CAN", "GND", S)

group("Power LED and ERC flags")
part("D4", "Device:LED", "GREEN PWR", "LED_SMD:LED_0603_1608Metric", "C2986059", S,
     {1: "PWR_LED_K", 2: "+3V3"})
R("2k", "PWR_LED_K", "GND", S)

for net in ["VBAT_RAW", "VBAT", "+5V", "+5V_FMU", "+3V3", "GND", "USB_VBUS_F"]:
    part(nref("#FLG"), "power:PWR_FLAG", "PWR_FLAG", "", "", S, {1: net})

# ======================= MCU =======================
S = "mcu"
MCU_PINS = {  # port -> net. Follows FMUv6C unless noted in PINMAP_NOTES
    # SPI1: ICM-45686
    "PA5": "SPI1_SCK_MCU", "PA6": "SPI1_MISO", "PA7": "SPI1_MOSI", "PC13": "IMU1_CS", "PE6": "IMU1_DRDY",
    # SPI2: BMI088
    "PD3": "SPI2_SCK_MCU", "PC2_C": "SPI2_MISO", "PC3_C": "SPI2_MOSI",
    "PC14": "BMI_GYRO_CS", "PC15": "BMI_ACC_CS", "PE5": "BMI_GYRO_DRDY", "PE4": "BMI_ACC_DRDY",
    "PB10": "IMU_CLKIN_MCU",
    # I2C
    "PD12": "I2C4_SCL", "PD13": "I2C4_SDA", "PB8": "I2C1_SCL", "PB7": "I2C1_SDA",
    # UARTs
    "PE8": "TELEM1_TX", "PE7": "TELEM1_RX", "PE9": "TELEM1_RTS", "PE10": "TELEM1_CTS",
    "PC12": "TELEM2_TX", "PD2": "TELEM2_RX", "PC8": "TELEM2_RTS", "PC9": "TELEM2_CTS",
    "PB6": "GPS_TX", "PA10": "GPS_RX",
    "PC6": "RC_TX", "PC7": "RC_RX",
    "PE0": "ESC_TLM_MCU",
    "PD8": "CONSOLE_TX", "PD9": "CONSOLE_RX",
    # CAN
    "PD1": "CAN1_TX", "PD0": "CAN1_RX", "PE12": "CAN1_STB",
    "PB13": "CAN2_TX", "PB5": "CAN2_RX", "PB12": "CAN2_STB",
    # SDMMC2
    "PD6": "SD_CLK_MCU", "PD7": "SD_CMD", "PB14": "SD_D0", "PB15": "SD_D1", "PB3": "SD_D2", "PB4": "SD_D3",
    # USB
    "PA11": "USB_DM", "PA12": "USB_DP", "PA9": "VBUS_SENSE",
    # motors (TIM1 = BDShot group, as FMUv6C)
    "PA8": "M1_MCU", "PE11": "M2_MCU", "PE13": "M3_MCU", "PE14": "M4_MCU",
    "PD14": "M5_MCU", "PD15": "M6_MCU", "PA0": "M7_MCU", "PA1": "M8_MCU",
    # ADC
    "PC5": "VBAT_SENSE", "PC4": "BATT_CURR_SENSE", "PA4": "V5_SENSE",
    # power control / status
    "PB2": "SENS_EN", "PE2": "PERIPH_EN", "PE3": "PERIPH_nOC", "PC10": "CAN5V_EN", "PC11": "CAN5V_nOC",
    "PA15": "MAIN_5V_DET", "PE15": "USB_PWR_SEL",
    "PB9": "HEATER_PWM", "PB0": "BUZZER",
    "PD10": "LED_R_N", "PD11": "LED_B_N", "PB1": "LED_G_N",
    # debug
    "PA13": "SWDIO", "PA14": "SWCLK",
    # clocks / system
    "PH0": "HSE_IN", "PH1": "HSE_OUT", "NRST": "NRST", "BOOT0": "BOOT0",
    "VBAT": "+3V3", "VDD": "+3V3", "VSS": "GND", "VSSA": "GND", "VDDA": "VDDA", "VREF+": "VDDA",
}
PINMAP_NOTES = [
    "BMI088 moved from SPI1 (FMUv6C) to SPI2 (PD3/PC2_C/PC3_C, FMUv6C's FRAM bus): each IMU on its own bus.",
    "No FRAM: PX4 parameters live on the microSD card.",
    "PB10 (FMUv6C I2C2_SCL) repurposed as TIM2_CH3 32 kHz IMU clock to ICM-45686 CLKIN (ARK Pi6X pattern).",
    "PE12 (FMUv6C HW_VER drive) -> CAN1 STB; PB12 (FMUv6C nPOWER_IN_B) -> CAN2 STB.",
    "PE0 UART8_RX -> ESC telemetry (FMUv6C GPS2). USART6 (FMUv6C PX4IO) -> RC receiver.",
    "PA15 -> buck-present detect; PE15 -> USB power-path status (LM66100 ST).",
    "PB1 (FMUv6C BATT2 voltage) -> green status LED.",
    "PC10/PC11 (FMUv6C 5V_HIPOWER EN/nOC) -> CAN connector power switch EN/nOC (active-high EN on TPS2553).",
]
group("STM32H743VIT6")
pins_db = json.load(open(os.path.join(HERE, "h743_pins.json")))
mcu = {}
used = set()
for num, name, typ, alts in pins_db:
    if name in MCU_PINS:
        net = MCU_PINS[name]
        if name == "VCAP":
            pass
        mcu[num] = net
        used.add(name)
    elif name == "VCAP":
        mcu[num] = f"VCAP{1 if num == 48 else 2}"
    else:
        mcu[num] = None  # no-connect
part("U10", "MCU_ST_STM32H7:STM32H743VITx", "STM32H743VIT6", "Package_QFP:LQFP-100_14x14mm_P0.5mm",
     "C114409", S, mcu)
group("Decoupling (AN4938)")
for i in range(5):
    C("100nF", "+3V3", "GND", S, note="VDD decoupling, one per VDD pin")
C("100nF", "+3V3", "GND", S, note="VBAT pin")
C("4.7uF", "+3V3", "GND", S, note="VDD bulk")
C("2.2uF", "VCAP1", "GND", S, note="VCAP, AN4938")
C("2.2uF", "VCAP2", "GND", S, note="VCAP, AN4938")
part("FB1", "Device:FerriteBead_Small", "220R@100MHz", "Inductor_SMD:L_0402_1005Metric", "C76885", S,
     {1: "+3V3", 2: "VDDA"}, note="BLM15AX221SN1D")
C("1uF", "VDDA", "GND", S)
C("100nF", "VDDA", "GND", S)
C("100nF", "VDDA", "GND", S, note="VREF+")
part(nref("#FLG"), "power:PWR_FLAG", "PWR_FLAG", "", "", S, {1: "VDDA"})
group("Reset, boot, clock")
C("100nF", "NRST", "GND", S)
R("10k", "BOOT0", "GND", S, note="BOOT0 low = run flash")
part("JP1", "Jumper:SolderJumper_2_Open", "BOOT0", "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", "", S,
     {1: "BOOT0", 2: "+3V3"}, note="bridge to enter ST ROM DFU on a blank chip")
part("Y1", "Device:Crystal_GND24", "16MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", "C13738", S,
     {1: "HSE_IN", 2: "GND", 3: "HSE_OUT", 4: "GND"}, note="X322516MLB4SI, same HSE as FMUv6C")
C("12pF", "HSE_IN", "GND", S, note="crystal CL = 9 pF: 2 x (9 - 3 pF stray)")
C("12pF", "HSE_OUT", "GND", S)
group("Series resistors at MCU")
R("33", "SPI1_SCK_MCU", "SPI1_SCK", S, note="SCK edge-rate series R at MCU")
R("33", "SPI2_SCK_MCU", "SPI2_SCK", S, note="SCK edge-rate series R at MCU")
R("22", "SD_CLK_MCU", "SD_CLK", S, note="SDMMC CLK series R at MCU")
R("33", "IMU_CLKIN_MCU", "IMU_CLKIN", S, note="32 kHz IMU clock series R")
group("Status LEDs")
for col, net, val, lcsc in [("RED", "LED_R_N", "1k", "C2286"), ("BLUE", "LED_B_N", "470", "C965807"),
                            ("GREEN", "LED_G_N", "470", "C2986059")]:
    k = net
    a = f"LED_{col[0]}_A"
    part({"RED":"D10","BLUE":"D11","GREEN":"D12"}[col], "Device:LED", col, "LED_SMD:LED_0603_1608Metric", lcsc, S, {1: k, 2: a})
    R(val, a, "+3V3", S)

# ======================= SENSORS =======================
S = "sensors"
group("IMU 1: ICM-45686 on SPI1")
part("U20", "fc_custom:ICM-45686", "ICM-45686", "Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y",
     "C22459454", S, {1: "SPI1_MISO", 2: None, 3: None, 4: "IMU1_DRDY", 5: "+3V3_SENS", 6: "GND", 7: None,
                      8: "+3V3_SENS", 9: "IMU_CLKIN", 10: None, 11: None, 12: "IMU1_CS", 13: "SPI1_SCK",
                      14: "SPI1_MOSI"}, note="primary IMU, SPI1, CLKIN on pin 9")
C("100nF", "+3V3_SENS", "GND", S, note="U20 VDD")
C("100nF", "+3V3_SENS", "GND", S, note="U20 VDDIO")
C("1uF", "+3V3_SENS", "GND", S, note="U20 bulk")
R("10k", "IMU1_CS", "+3V3_SENS", S, note="CS idle-high while MCU boots")
group("IMU 2: BMI088 on SPI2")
part("U21", "fc_custom:BMI088", "BMI088", "Package_LGA:Bosch_LGA-16_4.5x3mm_P0.5mm_LayoutBorder7x1y_ClockwisePinNumbering",
     "C194919", S, {14: "BMI_ACC_CS", 5: "BMI_GYRO_CS", 8: "SPI2_SCK", 9: "SPI2_MOSI", 15: "SPI2_MISO",
                    10: "SPI2_MISO", 7: "GND", 3: "+3V3_SENS", 2: "GND", 4: "GND", 11: "+3V3_SENS",
                    6: "GND", 16: "BMI_ACC_DRDY", 1: None, 12: "BMI_GYRO_DRDY", 13: None},
     note="secondary IMU (different vendor), SPI2, PS=GND selects SPI")
C("100nF", "+3V3_SENS", "GND", S, note="U21 VDD")
C("100nF", "+3V3_SENS", "GND", S, note="U21 VDDIO")
R("10k", "BMI_ACC_CS", "+3V3_SENS", S)
R("10k", "BMI_GYRO_CS", "+3V3_SENS", S)
group("Barometer: BMP581 on I2C4")
part("U22", "fc_custom:BMP581", "BMP581", "fc_custom:Bosch_LGA-10_2x2mm_P0.5mm_BMP581", "C5362283", S,
     {1: "+3V3_SENS", 2: "I2C4_SCL", 3: "GND", 4: "I2C4_SDA", 5: "BARO_SDO", 6: "+3V3_SENS", 7: "BARO_INT",
      8: "GND", 9: "GND", 10: "+3V3_SENS"}, note="I2C4 addr 0x47 (SDO high), CSB high = I2C, INT unused -> GND")
R("10k", "BARO_SDO", "+3V3_SENS", S, note="SDO high -> I2C address 0x47")
R("10k", "BARO_INT", "GND", S, note="INT unused; Bosch: tie low with int disabled")
C("100nF", "+3V3_SENS", "GND", S, note="U22 VDD")
C("100nF", "+3V3_SENS", "GND", S, note="U22 VDDIO")
R("2.2k", "I2C4_SCL", "+3V3_SENS", S)
R("2.2k", "I2C4_SDA", "+3V3_SENS", S)
group("IMU heater")
# IMU heater: 4 x 120R 1206 from +5V, ~0.83 W, PWM low-side switch
part("Q2", "Transistor_FET:AO3400A", "AO3400A", "Package_TO_SOT_SMD:SOT-23", "C20917", S,
     {1: "HEATER_G", 2: "GND", 3: "HEATER_LO"})
R("47", "HEATER_PWM", "HEATER_G", S)
R("100k", "HEATER_G", "GND", S, note="heater off while MCU boots")
for i in range(4):
    R("120", "+5V", "HEATER_LO", S, fp=R1206, lcsc="C17909", note="heater element, place around IMUs")

# ======================= STORAGE + USB =======================
S = "storage_usb"
group("USB-C device")
part("J20", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
     "C165948", S, {"A4": "USB_VBUS", "A9": "USB_VBUS", "B4": "USB_VBUS", "B9": "USB_VBUS",
                    "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "USB_SHIELD",
                    "A5": "USB_CC1", "B5": "USB_CC2", "A6": "USB_DP_C", "B6": "USB_DP_C",
                    "A7": "USB_DM_C", "B7": "USB_DM_C", "A8": None, "B8": None})
R("5.1k", "USB_CC1", "GND", S, note="UFP Rd")
R("5.1k", "USB_CC2", "GND", S, note="UFP Rd")
R("1M", "USB_SHIELD", "GND", S)
C("4.7nF", "USB_SHIELD", "GND", S)
part("U30", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", "C7519", S,
     {1: "USB_DP_C", 6: "USB_DP", 3: "USB_DM_C", 4: "USB_DM", 5: "USB_VBUS", 2: "GND"},
     note="flow-through: connector side 1/3, MCU side 6/4")
R("22k", "USB_VBUS", "VBUS_SENSE", S, note="VBUS detect, 5 V -> 3.0 V")
R("33k", "VBUS_SENSE", "GND", S)
part(nref("#FLG"), "power:PWR_FLAG", "PWR_FLAG", "", "", S, {1: "USB_VBUS"})
group("microSD (SDMMC2, 4-bit)")
part("J21", "Connector:Micro_SD_Card_Det_Hirose_DM3AT", "microSD", "Connector_Card:microSD_HC_Hirose_DM3AT-SF-PEJM5",
     "C114218", S, {1: "SD_D2", 2: "SD_D3", 3: "SD_CMD", 4: "+3V3", 5: "SD_CLK", 6: "GND", 7: "SD_D0",
                    8: "SD_D1", 9: None, 10: None, 11: "GND"}, note="SDMMC2 4-bit")
for n in ["SD_CMD", "SD_D0", "SD_D1", "SD_D2", "SD_D3"]:
    R("47k", n, "+3V3", S)
C("10uF", "+3V3", "GND", S, note="microSD")
C("100nF", "+3V3", "GND", S, note="microSD")

# ======================= CAN =======================
S = "can"
for bus, tx, rx, stb in [(1, "CAN1_TX", "CAN1_RX", "CAN1_STB"), (2, "CAN2_TX", "CAN2_RX", "CAN2_STB")]:
    group(f"CAN{bus}: TCAN1462V, split termination")
    part(f"U4{bus - 1}", "fc_custom:TCAN1462V", "TCAN1462VDRBRQ1", "fc_custom:TI_DRB0008J_VSON-8_3x3mm_P0.65mm",
         "C5215833", S, {1: tx, 2: "GND", 3: "+5V_FMU", 4: rx, 5: "+3V3", 6: f"CAN{bus}_L",
                         7: f"CAN{bus}_H", 8: stb, 9: "GND"},
         note="CAN FD 8 Mbit/s with signal-improvement; VIO = 3V3")
    C("100nF", "+5V_FMU", "GND", S, note=f"CAN{bus} VCC")
    C("1uF", "+5V_FMU", "GND", S, note=f"CAN{bus} VCC bulk")
    C("100nF", "+3V3", "GND", S, note=f"CAN{bus} VIO")
    part(f"JP4{bus}", "Jumper:SolderJumper_2_Bridged", "TERM", "Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm",
         "", S, {1: f"CAN{bus}_H", 2: f"CAN{bus}_TH"}, note="cut both jumpers to remove termination")
    part(f"JP5{bus}", "Jumper:SolderJumper_2_Bridged", "TERM", "Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm",
         "", S, {1: f"CAN{bus}_L", 2: f"CAN{bus}_TL"})
    R("60.4", f"CAN{bus}_TH", f"CAN{bus}_TM", S, note="split termination")
    R("60.4", f"CAN{bus}_TM", f"CAN{bus}_TL", S)
    C("4.7nF", f"CAN{bus}_TM", "GND", S)

# ======================= CONNECTORS =======================
S = "connectors"
GH4 = "Connector_JST:JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal"
GH6 = "Connector_JST:JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal"
SH6 = "Connector_JST:JST_SH_SM06B-SRSS-TB_1x06-1MP_P1.00mm_Horizontal"
SH8 = "Connector_JST:JST_SH_SM08B-SRSS-TB_1x08-1MP_P1.00mm_Horizontal"
group("CAN connectors")
part("J30", "Connector_Generic_MountingPin:Conn_01x04_MountingPin", "CAN1", GH4, "C189895", S,
     {1: "+5V_CAN", 2: "CAN1_H", 3: "CAN1_L", 4: "GND", "MP": "GND"}, note="DroneCAN flow + range module")
part("J31", "Connector_Generic_MountingPin:Conn_01x04_MountingPin", "CAN2", GH4, "C189895", S,
     {1: "+5V_CAN", 2: "CAN2_H", 3: "CAN2_L", 4: "GND", "MP": "GND"}, note="reserved: own ESC, CAN FD")
group("Serial ports")
part("J32", "Connector_Generic_MountingPin:Conn_01x06_MountingPin", "TELEM1", GH6, "C133065", S,
     {1: "+5V_PERIPH", 2: "TELEM1_TX", 3: "TELEM1_RX", 4: "TELEM1_CTS", 5: "TELEM1_RTS", 6: "GND", "MP": "GND"})
part("J33", "Connector_Generic_MountingPin:Conn_01x06_MountingPin", "TELEM2", GH6, "C133065", S,
     {1: "+5V_PERIPH", 2: "TELEM2_TX", 3: "TELEM2_RX", 4: "TELEM2_CTS", 5: "TELEM2_RTS", 6: "GND", "MP": "GND"},
     note="companion computer (uXRCE-DDS), flow control")
part("J34", "Connector_Generic_MountingPin:Conn_01x06_MountingPin", "GPS/I2C", GH6, "C133065", S,
     {1: "+5V_PERIPH", 2: "GPS_TX", 3: "GPS_RX", 4: "I2C1_SCL", 5: "I2C1_SDA", 6: "GND", "MP": "GND"})
R("2.2k", "I2C1_SCL", "+3V3", S)
R("2.2k", "I2C1_SDA", "+3V3", S)
part("J35", "Connector_Generic_MountingPin:Conn_01x04_MountingPin", "RC", GH4, "C189895", S,
     {1: "+5V_PERIPH", 2: "RC_TX", 3: "RC_RX", 4: "GND", "MP": "GND"}, note="CRSF/ELRS full duplex")
group("ESC harness (BDShot M1-M4, telemetry, current)")
part("J36", "Connector_Generic_MountingPin:Conn_01x08_MountingPin", "ESC", SH8, "C160407", S,
     {1: "VBAT_RAW", 2: "GND", 3: "ESC_CURR", 4: "ESC_TLM", 5: "M1", 6: "M2", 7: "M3", 8: "M4", "MP": "GND"},
     note="4-in-1 ESC harness")
for i in range(1, 5):
    R("47", f"M{i}_MCU", f"M{i}", S, note="motor line series R")
R("1k", "ESC_TLM", "ESC_TLM_MCU", S, note="ESC telemetry input protection")
part("U50", "Power_Protection:TPD4E05U06DQA", "TPD4E05U06DQAR", "Package_SON:USON-10_2.5x1.0mm_P0.5mm", "C138714",
     S, {1: "M1", 2: "M2", 4: "M3", 5: "M4", 3: "GND", 8: "GND", 6: None, 7: None, 9: None, 10: None},
     note="ESD on motor lines at the connector")
group("AUX: M5-M8, camera trigger/capture")
part("J37", "Connector_Generic_MountingPin:Conn_01x06_MountingPin", "AUX", SH6, "C56123098", S,
     {1: "+5V_PERIPH", 2: "M5", 3: "M6", 4: "M7", 5: "M8", 6: "GND", "MP": "GND"},
     note="M7 = camera trigger, M8 = camera capture (VIO time sync)")
for i in range(5, 9):
    R("47", f"M{i}_MCU", f"M{i}", S)
group("Debug (Pixhawk Debug Mini)")
part("J38", "Connector_Generic_MountingPin:Conn_01x06_MountingPin", "DEBUG", SH6, "C56123098", S,
     {1: "+3V3", 2: "CONSOLE_TX", 3: "CONSOLE_RX", 4: "SWDIO", 5: "SWCLK", 6: "GND", "MP": "GND"},
     note="Pixhawk Debug Mini pinout")
group("Buzzer")
part("J39", "Connector_Generic:Conn_01x02", "BUZZER", "fc_custom:Pads_2x_1.5x2mm", "", S,
     {1: "+5V", 2: "BUZZ_N"})
part("Q3", "Transistor_FET:2N7002", "2N7002", "Package_TO_SOT_SMD:SOT-23", "C8545", S,
     {1: "BUZZ_G", 2: "GND", 3: "BUZZ_N"})
R("100", "BUZZER", "BUZZ_G", S)
R("100k", "BUZZ_G", "GND", S)
part("D20", "Device:D_Schottky", "B5819W", "Diode_SMD:D_SOD-123", "C8598", S, {1: "+5V", 2: "BUZZ_N"},
     note="buzzer flyback")
group("Test points")
for net in ["VBAT", "+5V", "+5V_FMU", "+5V_PERIPH", "+5V_CAN", "+3V3", "+3V3_SENS", "CAN1_H", "CAN1_L",
            "SPI1_SCK", "CONSOLE_TX", "NRST", "GND"]:
    part(nref("TP"), "Connector:TestPoint", net, "TestPoint:TestPoint_Pad_D1.0mm", "", S, {1: net})
group("Mechanical")
for i in range(4):
    part(nref("H"), "Mechanical:MountingHole", "M3", "fc_custom:MountingHole_4.0mm_Grommet", "", S, {})
for i in range(3):
    part(nref("FID"), "Mechanical:Fiducial", "FID", "Fiducial:Fiducial_1mm_Mask2mm", "", S, {})


def nets():
    out = {}
    for p in PARTS:
        for pin, n in p["pins"].items():
            if n is None:
                continue
            out.setdefault(n, []).append((p["ref"], pin))
    return out


if __name__ == "__main__":
    ns = nets()
    singles = {n: v for n, v in ns.items() if len(v) < 2}
    print(len(PARTS), "parts,", len(ns), "nets")
    print("single-pin nets:", singles)
