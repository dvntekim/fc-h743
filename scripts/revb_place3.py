"""Rev B island placement, third pass. Heaters on F along the slot side; IMUs on B along the board
edge side, so the F area under each heater body (between its pads) and the B area beside the IMUs
line up into two via fields of ~2 x 5 vias. CS pull-ups move off the island."""
import pcbnew
b = pcbnew.LoadBoard("kicad/fc.kicad_pcb"); F = pcbnew.FromMM; mm = pcbnew.ToMM; V = lambda x, y: pcbnew.VECTOR2I(F(x), F(y))
PLACE = {"R44": ("F", 120.675, 78.9, 270), "R45": ("F", 120.675, 85.4, 90),
         "U23": ("F", 123.5, 77.9, 90), "C62": ("F", 123.5, 80.15, 90),
         "U21": ("B", 122.45, 78.2, 90), "U20": ("B", 122.45, 85.3, 0),
         "C48": ("B", 121.4, 81.4, 0), "C47": ("B", 124.0, 81.8, 90), "C44": ("B", 121.4, 83.1, 0),
         "C45": ("B", 122.9, 82.3, 90), "C46": ("B", 122.45, 87.45, 0),
         "R35": ("B", 110.0, 88.0, 0), "R36": ("B", 110.0, 89.2, 0), "R37": ("B", 110.0, 90.4, 0)}
for r, (side, x, y, a) in PLACE.items():
    f = b.FindFootprintByReference(r)
    if (side == "B") != f.IsFlipped():
        f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    f.SetPosition(V(x, y)); f.SetOrientationDegrees(a)
# everything of the island nets that is not locked goes; the heater spine is rebuilt
ISL = {"SPI1_SCK", "SPI1_MISO", "SPI1_MOSI", "IMU1_CS", "IMU1_DRDY", "IMU_CLKIN", "SPI2_SCK", "SPI2_MISO",
       "SPI2_MOSI", "BMI_ACC_CS", "BMI_GYRO_CS", "BMI_ACC_DRDY", "BMI_GYRO_DRDY", "+3V3_SENS"}
n = 0
for t in list(b.GetTracks()):
    pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
    on_isl = any(mm(p.x) >= 119.0 and mm(p.y) <= 89.0 for p in pts)
    if (t.GetNetname() in ISL and on_isl) or (t.GetNetname() in ("+5V", "HEATER_LO", "GND", "+3V3", "HEATER_G") and on_isl):
        b.Delete(t); n += 1
print("island copper removed", n)
def trk(net, w, pts, layer=pcbnew.F_Cu):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetLayer(layer); t.SetWidth(F(w)); t.SetStart(V(x1, y1)); t.SetEnd(V(x2, y2))
        t.SetNet(b.FindNet(net)); t.SetLocked(True); b.Add(t)
p = {(r, q.GetNumber()): (mm(q.GetX()), mm(q.GetY())) for r in ("R44", "R45") for q in b.FindFootprintByReference(r).Pads()}
top, bot = p[("R44", "1")], p[("R45", "1")]
trk("+5V", 0.3, [top, (122.35, top[1]), (122.35, bot[1]), bot])
lo1, lo2 = p[("R44", "2")], p[("R45", "2")]
trk("HEATER_LO", 0.4, [lo1, lo2])
via = pcbnew.PCB_VIA(b); via.SetPosition(V(lo1[0], (lo1[1] + lo2[1]) / 2)); via.SetWidth(F(0.45)); via.SetDrill(F(0.2))
via.SetNet(b.FindNet("HEATER_LO")); via.SetLocked(True); b.Add(via)
pcbnew.SaveBoard("kicad/fc.kicad_pcb", b); print("saved")
