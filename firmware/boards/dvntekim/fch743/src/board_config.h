/****************************************************************************
 *
 *   Copyright (c) 2022 PX4 Development Team. All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in
 *    the documentation and/or other materials provided with the
 *    distribution.
 * 3. Neither the name PX4 nor the names of its contributors may be
 *    used to endorse or promote products derived from this software
 *    without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 * FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 * COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 * BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
 * OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
 * AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
 * ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 *
 ****************************************************************************/

/**
 * @file board_config.h
 *
 * PX4FMU-v6c internal definitions
 */

#pragma once

/****************************************************************************************************
 * Included Files
 ****************************************************************************************************/

/**
 * @file board_config.h
 *
 * dvntekim fch743: GPS-denied quadrotor flight controller, STM32H743VIT6 (LQFP-100).
 * Pin map derived from PX4 FMUv6C; differences are marked "fch743:".
 * Hardware source of truth: github.com/dvntekim/fc-h743 (design.py / pinmap.md).
 */

#pragma once

#include <px4_platform_common/px4_config.h>
#include <nuttx/compiler.h>
#include <stdint.h>

#include <stm32_gpio.h>

/* LEDs: anodes to 3.3 V, MCU sinks (active low), same as FMUv6C plus green on PB1 */
#define GPIO_nLED_RED        /* PD10 */  (GPIO_OUTPUT|GPIO_PUSHPULL|GPIO_SPEED_50MHz|GPIO_OUTPUT_SET|GPIO_PORTD|GPIO_PIN10)
#define GPIO_nLED_BLUE       /* PD11 */  (GPIO_OUTPUT|GPIO_PUSHPULL|GPIO_SPEED_50MHz|GPIO_OUTPUT_SET|GPIO_PORTD|GPIO_PIN11)
#define GPIO_nLED_GREEN      /* PB1  */  (GPIO_OUTPUT|GPIO_PUSHPULL|GPIO_SPEED_50MHz|GPIO_OUTPUT_SET|GPIO_PORTB|GPIO_PIN1)

#define BOARD_HAS_CONTROL_STATUS_LEDS      1
#define BOARD_OVERLOAD_LED     LED_RED
#define BOARD_ARMED_STATE_LED  LED_BLUE

/* ADC: battery voltage (VBAT/11 divider), ESC current, scaled 5V_FMU (/2) */
#define ADC1_CH(n)                  (n)

#define PX4_ADC_GPIO  \
	/* PC4  */  GPIO_ADC12_INP4,   \
	/* PC5  */  GPIO_ADC12_INP8,   \
	/* PA4  */  GPIO_ADC12_INP18

#define ADC_BATTERY_CURRENT_CHANNEL             /* PC4 */  ADC1_CH(4)
#define ADC_BATTERY_VOLTAGE_CHANNEL             /* PC5 */  ADC1_CH(8)
#define ADC_SCALED_V5_CHANNEL                   /* PA4 */  ADC1_CH(18)

#define ADC_CHANNELS \
	((1 << ADC_BATTERY_CURRENT_CHANNEL) | \
	 (1 << ADC_BATTERY_VOLTAGE_CHANNEL)  | \
	 (1 << ADC_SCALED_V5_CHANNEL))

#define SYSTEM_ADC_BASE STM32_ADC1_BASE
#define BOARD_ADC_OPEN_CIRCUIT_V     (5.6f)
#define BOARD_BATTERY1_V_DIV         (11.0f)   /* 100k / 10k */

/* IMU heater: AO3400A low side, 4 x 120R around the IMUs (FMUv6C pin) */
#define GPIO_HEATER_OUTPUT
#define HEATER_NUM 	1
#define GPIO_HEATER1_OUTPUT  /* PB9  T17CH1 */ (GPIO_OUTPUT|GPIO_PUSHPULL|GPIO_SPEED_2MHz|GPIO_OUTPUT_CLEAR|GPIO_PORTB|GPIO_PIN9)
#define HEATER1_OUTPUT_EN(on_true)	       px4_arch_gpiowrite(GPIO_HEATER1_OUTPUT, (on_true))

/* PWM */
#define DIRECT_PWM_OUTPUT_CHANNELS   8
#define BOARD_NUM_IO_TIMERS 4

/* Power: fch743 has one brick (TPS54360B buck) and USB through LM66100 ideal diodes */
#define GPIO_MAIN_5V_DET         /* PA15 */ (GPIO_INPUT|GPIO_FLOAT|GPIO_PORTA|GPIO_PIN15)   /* high = buck up */
#define GPIO_USB_PWR_SEL         /* PE15 */ (GPIO_INPUT|GPIO_FLOAT|GPIO_PORTE|GPIO_PIN15)   /* high = running from USB */
#define BOARD_NUMBER_BRICKS      1

/* fch743: TPS2553 load switches are active-HIGH enable (FMUv6C uses active-low) */
#define GPIO_VDD_5V_PERIPH_EN     /* PE2  */ (GPIO_OUTPUT|GPIO_PUSHPULL|GPIO_SPEED_2MHz|GPIO_OUTPUT_SET|GPIO_PORTE|GPIO_PIN2)
#define GPIO_VDD_5V_PERIPH_nOC    /* PE3  */ (GPIO_INPUT |GPIO_FLOAT|GPIO_PORTE|GPIO_PIN3)
#define GPIO_VDD_5V_CAN_EN        /* PC10 */ (GPIO_OUTPUT|GPIO_PUSHPULL|GPIO_SPEED_2MHz|GPIO_OUTPUT_SET|GPIO_PORTC|GPIO_PIN10)
#define GPIO_VDD_5V_CAN_nOC       /* PC11 */ (GPIO_INPUT |GPIO_FLOAT|GPIO_PORTC|GPIO_PIN11)
#define GPIO_VDD_3V3_SENSORS_EN   /* PB2  */ (GPIO_OUTPUT|GPIO_PUSHPULL|GPIO_SPEED_2MHz|GPIO_OUTPUT_CLEAR|GPIO_PORTB|GPIO_PIN2)

#define VDD_5V_PERIPH_EN(on_true)          px4_arch_gpiowrite(GPIO_VDD_5V_PERIPH_EN, (on_true))
#define VDD_5V_HIPOWER_EN(on_true)         px4_arch_gpiowrite(GPIO_VDD_5V_CAN_EN, (on_true))
#define VDD_3V3_SENSORS_EN(on_true)        px4_arch_gpiowrite(GPIO_VDD_3V3_SENSORS_EN, (on_true))

/* fch743: CAN transceiver standby (TCAN1462V STB, high = standby). Driven low = normal. */
#define GPIO_CAN1_STB             /* PE12 */ (GPIO_OUTPUT|GPIO_PUSHPULL|GPIO_SPEED_2MHz|GPIO_OUTPUT_CLEAR|GPIO_PORTE|GPIO_PIN12)
#define GPIO_CAN2_STB             /* PB12 */ (GPIO_OUTPUT|GPIO_PUSHPULL|GPIO_SPEED_2MHz|GPIO_OUTPUT_CLEAR|GPIO_PORTB|GPIO_PIN12)

/* fch743: 32 kHz IMU clock to ICM-45686 CLKIN, TIM2_CH3 on PB10 (AF1) */
#define GPIO_IMU_CLKIN            /* PB10 */ (GPIO_ALT|GPIO_AF1|GPIO_SPEED_50MHz|GPIO_PUSHPULL|GPIO_PORTB|GPIO_PIN10)
#define BOARD_IMU_CLKIN_HZ        32000
/* PB10 parked (input, pull-down) while +3V3_SENS is off, so the clock cannot back-power the ICM-45686 */
#define GPIO_IMU_CLKIN_OFF        /* PB10 */ (GPIO_INPUT|GPIO_PULLDOWN|GPIO_SPEED_2MHz|GPIO_PORTB|GPIO_PIN10)

/* Tone alarm output (buzzer pads) */
#define TONE_ALARM_TIMER        3  /* Timer 3 */
#define TONE_ALARM_CHANNEL      3  /* PB0 GPIO_TIM3_CH3OUT_1 */
#define GPIO_BUZZER_1           /* PB0 */ (GPIO_OUTPUT|GPIO_PUSHPULL|GPIO_SPEED_2MHz|GPIO_OUTPUT_CLEAR|GPIO_PORTB|GPIO_PIN0)
#define GPIO_TONE_ALARM_IDLE    GPIO_BUZZER_1
#define GPIO_TONE_ALARM         GPIO_TIM3_CH3OUT_1

/* USB OTG FS: VBUS sense through 22k/33k divider */
#define GPIO_OTGFS_VBUS         /* PA9 */ (GPIO_INPUT|GPIO_PULLDOWN|GPIO_SPEED_100MHz|GPIO_PORTA|GPIO_PIN9)

/* High-resolution timer */
#define HRT_TIMER               8  /* use timer8 for the HRT */
#define HRT_TIMER_CHANNEL       3  /* use capture/compare channel 3 */

/* RC: CRSF/ELRS full duplex on USART6 (FMUv6C's PX4IO port) */
#define RC_SERIAL_PORT          "/dev/ttyS4"
#define BOARD_SUPPORTS_RC_SERIAL_PORT_OUTPUT

/* SD card on SDMMC2 */
#define SDIO_SLOTNO                    0
#define SDIO_MINOR                     0

#define BOARD_ADC_USB_CONNECTED (px4_arch_gpioread(GPIO_OTGFS_VBUS))
#define BOARD_ADC_USB_VALID     (px4_arch_gpioread(GPIO_USB_PWR_SEL))
#define BOARD_ADC_SERVO_VALID   (1)
#define BOARD_ADC_BRICK_VALID   (px4_arch_gpioread(GPIO_MAIN_5V_DET))
#define BOARD_ADC_PERIPH_5V_OC  (!px4_arch_gpioread(GPIO_VDD_5V_PERIPH_nOC))
#define BOARD_ADC_HIPOWER_5V_OC (!px4_arch_gpioread(GPIO_VDD_5V_CAN_nOC))

#define BOARD_DMA_ALLOC_POOL_SIZE 5120
#define BOARD_HAS_ON_RESET 1

#define PX4_GPIO_INIT_LIST { \
		PX4_ADC_GPIO,                     \
		GPIO_CAN1_TX,                     \
		GPIO_CAN1_RX,                     \
		GPIO_CAN2_TX,                     \
		GPIO_CAN2_RX,                     \
		GPIO_CAN1_STB,                    \
		GPIO_CAN2_STB,                    \
		GPIO_HEATER1_OUTPUT,              \
		GPIO_MAIN_5V_DET,                 \
		GPIO_USB_PWR_SEL,                 \
		GPIO_VDD_5V_PERIPH_EN,            \
		GPIO_VDD_5V_PERIPH_nOC,           \
		GPIO_VDD_5V_CAN_EN,               \
		GPIO_VDD_5V_CAN_nOC,              \
		GPIO_VDD_3V3_SENSORS_EN,          \
		GPIO_TONE_ALARM_IDLE,             \
		GPIO_IMU_CLKIN,                   \
	}

#define BOARD_ENABLE_CONSOLE_BUFFER

__BEGIN_DECLS

#ifndef __ASSEMBLY__

int stm32_sdio_initialize(void);
extern void stm32_spiinitialize(void);
extern void stm32_usbinitialize(void);
extern void board_peripheral_reset(int ms);
extern void board_imu_clkin_start(void);
extern void board_imu_clkin_stop(void);

#include <px4_platform_common/board_common.h>

#endif /* __ASSEMBLY__ */

__END_DECLS
