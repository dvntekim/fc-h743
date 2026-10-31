# Pin map check (STM32H743VIT6, LQFP-100)

Alternate functions are checked against ST's pin data as shipped in the KiCad `MCU_ST_STM32H7:STM32H743VITx` symbol. `FMUv6C` shows what PX4's Pixhawk 6C target uses the same pin for.

| Pin | Port | Net | Function needed | AF check | FMUv6C use |
|---|---|---|---|---|---|
| 1 | PE2 | PERIPH_EN | GPIO | OK | 5V periph EN |
| 2 | PE3 | PERIPH_nOC | GPIO | OK | 5V periph OC |
| 3 | PE4 | BMI_ACC_DRDY | GPIO | OK | BMI088 accel DRDY |
| 4 | PE5 | BMI_GYRO_DRDY | GPIO | OK | BMI088 gyro DRDY |
| 5 | PE6 | IMU1_DRDY | GPIO | OK | ICM42688P DRDY |
| 7 | PC13 | IMU1_CS | GPIO | OK | ICM42688P CS |
| 8 | PC14 | BMI_GYRO_CS | GPIO | OK | BMI088 gyro CS |
| 9 | PC15 | BMI_ACC_CS | GPIO | OK | BMI088 accel CS |
| 12 | PH0 | HSE_IN | RCC_OSC_IN | OK | - |
| 13 | PH1 | HSE_OUT | RCC_OSC_OUT | OK | - |
| 17 | PC2_C | SPI2_MISO | SPI2_MISO | OK | SPI2_MISO |
| 18 | PC3_C | SPI2_MOSI | SPI2_MOSI | OK | SPI2_MOSI |
| 22 | PA0 | M7_MCU | TIM5_CH1 | OK | TIM5_CH1 |
| 23 | PA1 | M8_MCU | TIM5_CH2 | OK | TIM5_CH2 |
| 28 | PA4 | V5_SENSE | ADC1_INP18 | OK | ADC scaled 5V |
| 29 | PA5 | SPI1_SCK_MCU | SPI1_SCK | OK | SPI1_SCK |
| 30 | PA6 | SPI1_MISO | SPI1_MISO | OK | SPI1_MISO |
| 31 | PA7 | SPI1_MOSI | SPI1_MOSI | OK | SPI1_MOSI |
| 32 | PC4 | BATT_CURR_SENSE | ADC1_INP4 | OK | ADC BATT1 I |
| 33 | PC5 | VBAT_SENSE | ADC1_INP8 | OK | ADC BATT1 V |
| 34 | PB0 | BUZZER | TIM3_CH3 | OK | buzzer TIM3_CH3 |
| 35 | PB1 | LED_G_N | GPIO | OK | - |
| 36 | PB2 | SENS_EN | GPIO | OK | 3V3 sensors EN |
| 37 | PE7 | TELEM1_RX | UART7_RX | OK | UART7_RX |
| 38 | PE8 | TELEM1_TX | UART7_TX | OK | UART7_TX |
| 39 | PE9 | TELEM1_RTS | UART7_RTS | OK | UART7_RTS |
| 40 | PE10 | TELEM1_CTS | UART7_CTS | OK | UART7_CTS |
| 41 | PE11 | M2_MCU | TIM1_CH2 | OK | TIM1_CH2 |
| 42 | PE12 | CAN1_STB | GPIO | OK | - |
| 43 | PE13 | M3_MCU | TIM1_CH3 | OK | TIM1_CH3 |
| 44 | PE14 | M4_MCU | TIM1_CH4 | OK | TIM1_CH4 |
| 45 | PE15 | USB_PWR_SEL | GPIO | OK | USB valid |
| 46 | PB10 | IMU_CLKIN_MCU | TIM2_CH3 | OK | - |
| 51 | PB12 | CAN2_STB | GPIO | OK | - |
| 52 | PB13 | CAN2_TX | FDCAN2_TX | OK | FDCAN2_TX |
| 53 | PB14 | SD_D0 | SDMMC2_D0 | OK | - |
| 54 | PB15 | SD_D1 | SDMMC2_D1 | OK | - |
| 55 | PD8 | CONSOLE_TX | USART3_TX | OK | USART3_TX |
| 56 | PD9 | CONSOLE_RX | USART3_RX | OK | USART3_RX |
| 57 | PD10 | LED_R_N | GPIO | OK | LED red |
| 58 | PD11 | LED_B_N | GPIO | OK | LED blue |
| 59 | PD12 | I2C4_SCL | I2C4_SCL | OK | I2C4_SCL |
| 60 | PD13 | I2C4_SDA | I2C4_SDA | OK | I2C4_SDA |
| 61 | PD14 | M5_MCU | TIM4_CH3 | OK | TIM4_CH3 |
| 62 | PD15 | M6_MCU | TIM4_CH4 | OK | TIM4_CH4 |
| 63 | PC6 | RC_TX | USART6_TX | OK | USART6_TX |
| 64 | PC7 | RC_RX | USART6_RX | OK | USART6_RX |
| 65 | PC8 | TELEM2_RTS | UART5_RTS | OK | - |
| 66 | PC9 | TELEM2_CTS | UART5_CTS | OK | UART5_CTS |
| 67 | PA8 | M1_MCU | TIM1_CH1 | OK | TIM1_CH1 |
| 68 | PA9 | VBUS_SENSE | GPIO | OK | OTG VBUS |
| 69 | PA10 | GPS_RX | USART1_RX | OK | USART1_RX |
| 70 | PA11 | USB_DM | USB_OTG_FS_DM | OK | - |
| 71 | PA12 | USB_DP | USB_OTG_FS_DP | OK | - |
| 72 | PA13 | SWDIO | DEBUG_JTMS-SWDIO | OK | - |
| 76 | PA14 | SWCLK | DEBUG_JTCK-SWCLK | OK | - |
| 77 | PA15 | MAIN_5V_DET | GPIO | OK | brick1 valid |
| 78 | PC10 | CAN5V_EN | GPIO | OK | 5V hipower EN |
| 79 | PC11 | CAN5V_nOC | GPIO | OK | 5V hipower OC |
| 80 | PC12 | TELEM2_TX | UART5_TX | OK | UART5_TX |
| 81 | PD0 | CAN1_RX | FDCAN1_RX | OK | FDCAN1_RX |
| 82 | PD1 | CAN1_TX | FDCAN1_TX | OK | FDCAN1_TX |
| 83 | PD2 | TELEM2_RX | UART5_RX | OK | UART5_RX |
| 84 | PD3 | SPI2_SCK_MCU | SPI2_SCK | OK | SPI2_SCK |
| 87 | PD6 | SD_CLK_MCU | SDMMC2_CK | OK | SDMMC2_CK |
| 88 | PD7 | SD_CMD | SDMMC2_CMD | OK | SDMMC2_CMD |
| 89 | PB3 | SD_D2 | SDMMC2_D2 | OK | SDMMC2_D2 |
| 90 | PB4 | SD_D3 | SDMMC2_D3 | OK | - |
| 91 | PB5 | CAN2_RX | FDCAN2_RX | OK | FDCAN2_RX |
| 92 | PB6 | GPS_TX | USART1_TX | OK | USART1_TX |
| 93 | PB7 | I2C1_SDA | I2C1_SDA | OK | I2C1_SDA |
| 95 | PB8 | I2C1_SCL | I2C1_SCL | OK | I2C1_SCL |
| 96 | PB9 | HEATER_PWM | TIM17_CH1 | OK | heater TIM17_CH1 |
| 97 | PE0 | ESC_TLM_MCU | UART8_RX | OK | UART8_RX |

## Timers

- TIM1: CH1=PA8(M1_MCU), CH2=PE11(M2_MCU), CH3=PE13(M3_MCU), CH4=PE14(M4_MCU)
- TIM17: CH1=PB9(HEATER_PWM)
- TIM2: CH3=PB10(IMU_CLKIN_MCU)
- TIM3: CH3=PB0(BUZZER)
- TIM4: CH3=PD14(M5_MCU), CH4=PD15(M6_MCU)
- TIM5: CH1=PA0(M7_MCU), CH2=PA1(M8_MCU)

TIM8 is PX4's HRT on FMUv6C (no pins). TIM2 only drives the 32 kHz IMU clock.

## Deviations from FMUv6C

- BMI088 moved from SPI1 (FMUv6C) to SPI2 (PD3/PC2_C/PC3_C, FMUv6C's FRAM bus): each IMU on its own bus.
- No FRAM: PX4 parameters live on the microSD card.
- PB10 (FMUv6C I2C2_SCL) repurposed as TIM2_CH3 32 kHz IMU clock to ICM-45686 CLKIN (ARK Pi6X pattern).
- PE12 (FMUv6C HW_VER drive) -> CAN1 STB; PB12 (FMUv6C nPOWER_IN_B) -> CAN2 STB.
- PE0 UART8_RX -> ESC telemetry (FMUv6C GPS2). USART6 (FMUv6C PX4IO) -> RC receiver.
- PA15 -> buck-present detect; PE15 -> USB power-path status (LM66100 ST).
- PB1 (FMUv6C BATT2 voltage) -> green status LED.
- PC10/PC11 (FMUv6C 5V_HIPOWER EN/nOC) -> CAN connector power switch EN/nOC (active-high EN on TPS2553).

## Result

PASS: no conflicts
