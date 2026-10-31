"""Bosch BMP581 I2C peer for Simantic.

From BST-BMP581-DS004-13 (sec. 7) and PX4 src/drivers/barometer/bmp581:
  CHIP_ID 0x01 -> 0x50, REV_ID 0x02 -> 0x32
  STATUS  0x28 -> 0x02 (nvm_rdy, no nvm_err)
  INT_STATUS 0x27 bit4 'POR/soft-reset complete', clears on read
  CMD 0x7E <- 0xB6 soft reset
Pressure/temperature registers hold a fixed 101325 Pa / 25 C so the driver publishes real values.
"""
CHIP_ID, REV_ID, INT_STATUS, STATUS, CMD = 0x01, 0x02, 0x27, 0x28, 0x7E
P_PA, T_C = 101325.0, 25.0


class Slave:
    def __init__(self, ctx):
        self.ctx = ctx
        self.ptr = 0
        self._power_on()

    def _power_on(self):
        r = bytearray(128)
        r[CHIP_ID] = 0x50; r[REV_ID] = 0x32
        r[INT_STATUS] = 0x10; r[STATUS] = 0x02
        r[0x37] = 0x70; r[0x30] = 0x03           # ODR_CONFIG, DSP_CONFIG reset values
        t = int(T_C * 65536); p = int(P_PA * 64)
        r[0x1D:0x20] = bytes([t & 0xFF, (t >> 8) & 0xFF, (t >> 16) & 0xFF])
        r[0x20:0x23] = bytes([p & 0xFF, (p >> 8) & 0xFF, (p >> 16) & 0xFF])
        self.regs = r

    def on_write(self, data):
        if not data:
            return
        self.ptr = data[0] & 0x7F
        for b in data[1:]:
            if self.ptr == CMD and b == 0xB6:
                self.ctx.info("soft reset")
                self._power_on()
            elif self.ptr not in (CHIP_ID, REV_ID, STATUS):
                self.regs[self.ptr] = b
            self.ptr = (self.ptr + 1) & 0x7F

    def on_read(self, count):
        out = bytearray()
        for _ in range(count):
            out.append(self.regs[self.ptr])
            if self.ptr == INT_STATUS:
                self.regs[INT_STATUS] = 0
            self.ptr = (self.ptr + 1) & 0x7F
        return bytes(out)
