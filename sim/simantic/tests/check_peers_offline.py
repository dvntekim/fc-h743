"""Offline checks of the peers with a fake ctx (no simulator needed)."""
import importlib.util, pathlib, sys
PEERS = pathlib.Path(__file__).resolve().parent.parent / "peers"


def load(n):
    s = importlib.util.spec_from_file_location(n, PEERS / f"{n}.py"); m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m); return m


class Ctx:
    def __init__(self): self.logs, self.sent, self.periodic = [], [], None
    def info(self, m): self.logs.append(m)
    def send(self, i, d, extended=False, **k): self.sent.append((i, bytes(d), extended))
    def schedule_periodic(self, us): self.periodic = us


def xfer(s, tx):
    s.on_select(); rx = [s.on_transmit(b) for b in tx]; s.on_deselect(); return rx


icm = load("icm45686_peer").Slave(Ctx())
assert xfer(icm, [0xF2, 0]) == [0, 0xE9], "ICM-45686 WHO_AM_I"
xfer(icm, [0x10, 0x0F]); assert xfer(icm, [0x90, 0])[1] == 0x0F, "PWR_MGMT0 readback"
xfer(icm, [0x7C, 0xA4, 0xA6]); xfer(icm, [0x7E, 0x55])
xfer(icm, [0x7C, 0xA4, 0xA6]); assert xfer(icm, [0xFE, 0])[1] == 0x55, "IREG readback"
xfer(icm, [0x7F, 0x02]); assert xfer(icm, [0x90, 0])[1] == 0 and xfer(icm, [0xFF, 0])[1] & 2 == 0, "soft reset"
acc = load("bmi088_accel_peer").Slave(Ctx()); assert xfer(acc, [0x80, 0, 0])[2] == 0x1E
gyr = load("bmi088_gyro_peer").Slave(Ctx()); assert xfer(gyr, [0x80, 0])[1] == 0x0F
b = load("bmp581_peer").Slave(Ctx())
b.on_write(bytes([0x01])); assert b.on_read(2) == bytes([0x50, 0x32])
b.on_write(bytes([0x7E, 0xB6])); b.on_write(bytes([0x28])); assert b.on_read(1)[0] & 0x06 == 0x02
b.on_write(bytes([0x27])); assert b.on_read(1)[0] & 0x10; b.on_write(bytes([0x27])); assert b.on_read(1)[0] == 0
b.on_write(bytes([0x1D])); d = b.on_read(6)
assert abs(int.from_bytes(d[3:6], "little") / 64 - 101325) < 1 and abs(int.from_bytes(d[0:3], "little") / 65536 - 25) < 0.01
print("all peer checks passed")
