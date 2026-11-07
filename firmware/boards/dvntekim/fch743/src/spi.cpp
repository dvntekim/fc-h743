/* fch743 SPI buses: each IMU on its own bus (FMUv6C puts both on SPI1).
 * SPI1: ICM-45686  CS PC13  DRDY PE6   (bus power: 3V3_SENS enable PB2)
 * SPI2: BMI088     gyro CS PC14 DRDY PE5, accel CS PC15 DRDY PE4 */
#include <px4_arch/spi_hw_description.h>
#include <drivers/drv_sensor.h>
#include <nuttx/spi/spi.h>

constexpr px4_spi_bus_t px4_spi_buses[SPI_BUS_MAX_BUS_ITEMS] = {
	initSPIBus(SPI::Bus::SPI1, {
		initSPIDevice(DRV_IMU_DEVTYPE_ICM45686, SPI::CS{GPIO::PortC, GPIO::Pin13}, SPI::DRDY{GPIO::PortE, GPIO::Pin6}),
	}, {GPIO::PortB, GPIO::Pin2}),
	initSPIBus(SPI::Bus::SPI2, {
		initSPIDevice(DRV_GYR_DEVTYPE_BMI088, SPI::CS{GPIO::PortC, GPIO::Pin14}, SPI::DRDY{GPIO::PortE, GPIO::Pin5}),
		initSPIDevice(DRV_ACC_DEVTYPE_BMI088, SPI::CS{GPIO::PortC, GPIO::Pin15}, SPI::DRDY{GPIO::PortE, GPIO::Pin4}),
	}, {GPIO::PortB, GPIO::Pin2}), /* BMI088 is on +3V3_SENS too: park SPI2 pins when PB2 cuts the rail */
};

static constexpr bool unused = validateSPIConfig(px4_spi_buses);
