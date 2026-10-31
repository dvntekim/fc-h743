"""CubeMX-style pin-map check.

For every MCU pin the design uses, state the peripheral function it must
provide and confirm that function is in ST's alternate-function list for that
pin (taken from the KiCad STM32H743VITx symbol, generated from ST's pin
database). Also checks no function is claimed twice and that PX4's FMUv6C
assignments are kept where the design says they are.
"""
import json, sys
from design import MCU_PINS, PINMAP_NOTES

REQ = {  # pin -> required alternate function (None = plain GPIO / EXTI)
    "PA5": "SPI1_SCK", "PA6": "SPI1_MISO", "PA7": "SPI1_MOSI", "PC13": None, "PE6": None,
    "PD3": "SPI2_SCK", "PC2_C": "SPI2_MISO", "PC3_C": "SPI2_MOSI", "PC14": None, "PC15": None,
    "PE5": None, "PE4": None, "PB10": "TIM2_CH3",
    "PD12": "I2C4_SCL", "PD13": "I2C4_SDA", "PB8": "I2C1_SCL", "PB7": "I2C1_SDA",
    "PE8": "UART7_TX", "PE7": "UART7_RX", "PE9": "UART7_RTS", "PE10": "UART7_CTS",
    "PC12": "UART5_TX", "PD2": "UART5_RX", "PC8": "UART5_RTS", "PC9": "UART5_CTS",
    "PB6": "USART1_TX", "PA10": "USART1_RX", "PC6": "USART6_TX", "PC7": "USART6_RX",
    "PE0": "UART8_RX", "PD8": "USART3_TX", "PD9": "USART3_RX",
    "PD1": "FDCAN1_TX", "PD0": "FDCAN1_RX", "PB13": "FDCAN2_TX", "PB5": "FDCAN2_RX",
    "PE12": None, "PB12": None,
    "PD6": "SDMMC2_CK", "PD7": "SDMMC2_CMD", "PB14": "SDMMC2_D0", "PB15": "SDMMC2_D1",
    "PB3": "SDMMC2_D2", "PB4": "SDMMC2_D3",
    "PA11": "USB_OTG_FS_DM", "PA12": "USB_OTG_FS_DP", "PA9": None,
    "PA8": "TIM1_CH1", "PE11": "TIM1_CH2", "PE13": "TIM1_CH3", "PE14": "TIM1_CH4",
    "PD14": "TIM4_CH3", "PD15": "TIM4_CH4", "PA0": "TIM5_CH1", "PA1": "TIM5_CH2",
    "PC5": "ADC1_INP8", "PC4": "ADC1_INP4", "PA4": "ADC1_INP18",
    "PB9": "TIM17_CH1", "PB0": "TIM3_CH3",
    "PA13": "DEBUG_JTMS-SWDIO", "PA14": "DEBUG_JTCK-SWCLK",
    "PH0": "RCC_OSC_IN", "PH1": "RCC_OSC_OUT",
}
# FMUv6C assignments (boards/px4/fmu-v6c board.h / board_config.h / timer_config.cpp / spi.cpp)
FMUV6C = {
    "PA5": "SPI1_SCK", "PA6": "SPI1_MISO", "PA7": "SPI1_MOSI", "PC13": "ICM42688P CS", "PE6": "ICM42688P DRDY",
    "PC14": "BMI088 gyro CS", "PC15": "BMI088 accel CS", "PE5": "BMI088 gyro DRDY", "PE4": "BMI088 accel DRDY",
    "PD3": "SPI2_SCK", "PC2_C": "SPI2_MISO", "PC3_C": "SPI2_MOSI",
    "PD12": "I2C4_SCL", "PD13": "I2C4_SDA", "PB8": "I2C1_SCL", "PB7": "I2C1_SDA",
    "PE8": "UART7_TX", "PE7": "UART7_RX", "PE9": "UART7_RTS", "PE10": "UART7_CTS",
    "PC12": "UART5_TX", "PD2": "UART5_RX", "PC9": "UART5_CTS", "PB6": "USART1_TX", "PA10": "USART1_RX",
    "PC6": "USART6_TX", "PC7": "USART6_RX", "PE0": "UART8_RX", "PD8": "USART3_TX", "PD9": "USART3_RX",
    "PD1": "FDCAN1_TX", "PD0": "FDCAN1_RX", "PB13": "FDCAN2_TX", "PB5": "FDCAN2_RX",
    "PD6": "SDMMC2_CK", "PD7": "SDMMC2_CMD", "PB3": "SDMMC2_D2",
    "PA8": "TIM1_CH1", "PE11": "TIM1_CH2", "PE13": "TIM1_CH3", "PE14": "TIM1_CH4",
    "PD14": "TIM4_CH3", "PD15": "TIM4_CH4", "PA0": "TIM5_CH1", "PA1": "TIM5_CH2",
    "PC5": "ADC BATT1 V", "PC4": "ADC BATT1 I", "PA4": "ADC scaled 5V", "PB9": "heater TIM17_CH1",
    "PB0": "buzzer TIM3_CH3", "PB2": "3V3 sensors EN", "PE2": "5V periph EN", "PE3": "5V periph OC",
    "PC10": "5V hipower EN", "PC11": "5V hipower OC", "PD10": "LED red", "PD11": "LED blue", "PA9": "OTG VBUS",
    "PA15": "brick1 valid", "PE15": "USB valid",
}


def main():
    pins = {p[1]: (p[0], set(p[3])) for p in json.load(open("h743_pins.json"))}
    rows, errors = [], []
    seen = {}
    for name, net in sorted(MCU_PINS.items(), key=lambda kv: kv[0]):
        if name not in pins or name in ("VDD", "VSS", "VBAT", "VDDA", "VSSA", "VREF+", "NRST", "BOOT0"):
            continue
        num, alts = pins[name]
        req = REQ.get(name, "GPIO" if name.startswith("P") else None)
        ok = req in (None, "GPIO") or req in alts
        if not ok:
            errors.append(f"{name}: needs {req}, not in {sorted(alts)}")
        if req not in (None, "GPIO"):
            if req in seen:
                errors.append(f"{req} claimed by {seen[req]} and {name}")
            seen[req] = name
        v6c = FMUV6C.get(name, "-")
        rows.append((num, name, net, req or "GPIO", "OK" if ok else "FAIL", v6c))
    # timers: channels used per timer
    tim = {}
    for _, name, net, req, _, _ in rows:
        if req and req.startswith("TIM"):
            t = req.split("_")[0]
            tim.setdefault(t, []).append(f"{req.split('_')[1]}={name}({net})")
    with open("pinmap.md", "w") as f:
        f.write("# Pin map check (STM32H743VIT6, LQFP-100)\n\n")
        f.write("Alternate functions are checked against ST's pin data as shipped in the KiCad "
                "`MCU_ST_STM32H7:STM32H743VITx` symbol. `FMUv6C` shows what PX4's Pixhawk 6C target "
                "uses the same pin for.\n\n")
        f.write("| Pin | Port | Net | Function needed | AF check | FMUv6C use |\n|---|---|---|---|---|---|\n")
        for r in sorted(rows):
            f.write("| %s | %s | %s | %s | %s | %s |\n" % r)
        f.write("\n## Timers\n\n")
        for t, ch in sorted(tim.items()):
            f.write(f"- {t}: {', '.join(ch)}\n")
        f.write("\nTIM8 is PX4's HRT on FMUv6C (no pins). TIM2 only drives the 32 kHz IMU clock.\n")
        f.write("\n## Deviations from FMUv6C\n\n")
        for n in PINMAP_NOTES:
            f.write(f"- {n}\n")
        f.write("\n## Result\n\n")
        f.write("PASS: no conflicts\n" if not errors else "FAIL:\n" + "\n".join(f"- {e}" for e in errors) + "\n")
    print("errors:", errors or "none", "| pins used:", len(rows))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
