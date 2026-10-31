/* fch743 I2C: I2C1 external (GPS/I2C connector), I2C4 internal (BMP581 @ 0x47) */
#include <px4_arch/i2c_hw_description.h>

constexpr px4_i2c_bus_t px4_i2c_buses[I2C_BUS_MAX_BUS_ITEMS] = {
	initI2CBusExternal(1),
	initI2CBusInternal(4),
};
