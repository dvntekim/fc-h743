"""TDK ICM-45686 SPI peer for Simantic (register-level, no motion data).

From TDK DS-000489 rev 1.1 and PX4 src/drivers/imu/invensense/icm45686:
  WHO_AM_I    0x72 -> 0xE9
  REG_MISC2   0x7F  bit1 SOFT_RST (self-clearing)
  IREG_ADDR   0x7C/0x7D, IREG_DATA 0x7E  (indirect registers, address auto-increments)
SPI framing: first byte = address, bit7 set for read; burst auto-increments.
"""
WHO_AM_I, WHOAMI_VALUE = 0x72, 0xE9
REG_MISC2, SOFT_RST = 0x7F, 0x02
IREG_HI, IREG_LO, IREG_DATA = 0x7C, 0x7D, 0x7E


class Slave:
    def __init__(self, ctx):
        self.ctx = ctx
        self._power_on()
        self.addr = None
        self.read = False

    def _power_on(self):
        self.regs = bytearray(128)
        self.regs[WHO_AM_I] = WHOAMI_VALUE
        self.ireg = {}
        self.iaddr = 0

    def on_select(self):
        self.addr = None

    def on_deselect(self):
        self.addr = None

    def on_transmit(self, b):
        if self.addr is None:
            self.read = bool(b & 0x80)
            self.addr = b & 0x7F
            return 0x00
        a = self.addr
        if self.read:
            if a == IREG_DATA:
                v = self.ireg.get(self.iaddr, 0); self.iaddr = (self.iaddr + 1) & 0xFFFF
            else:
                v = self.regs[a]
            if a != IREG_DATA:
                self.addr = (a + 1) & 0x7F
            return v
        # write
        if a == REG_MISC2 and b & SOFT_RST:
            self.ctx.info("soft reset")
            self._power_on()
        elif a == IREG_HI:
            self.iaddr = (b << 8) | (self.iaddr & 0xFF); self.regs[a] = b
        elif a == IREG_LO:
            self.iaddr = (self.iaddr & 0xFF00) | b; self.regs[a] = b
        elif a == IREG_DATA:
            self.ireg[self.iaddr] = b; self.iaddr = (self.iaddr + 1) & 0xFFFF
        elif a != WHO_AM_I:
            self.regs[a] = b
        if a != IREG_DATA:
            self.addr = (a + 1) & 0x7F
        return 0x00
