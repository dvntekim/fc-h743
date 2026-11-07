"""Rev B heaters in series: R44 (+5V -> MID) top, R45 (MID -> LO) bottom, both pad 1 up.
+5V spine on F down the right lane and under R45 to the bridge; HEATER_LO leaves R45's bottom-left
corner to the bridge on F above it; MID joins the two inner pads. No vias."""
import pcbnew
b = pcbnew.LoadBoard("kicad/fc.kicad_pcb"); F = pcbnew.FromMM; V = lambda x, y: pcbnew.VECTOR2I(F(x), F(y)); mm = pcbnew.ToMM
r44, r45 = b.FindFootprintByReference("R44"), b.FindFootprintByReference("R45")
r44.SetPosition(V(120.675, 78.9)); r44.SetOrientationDegrees(270)
r45.SetPosition(V(120.675, 85.1)); r45.SetOrientationDegrees(270)
n = 0
for t in list(b.GetTracks()):
    if t.GetNetname() not in ("+5V", "HEATER_LO", "HEATER_MID"): continue
    pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
    if any(mm(p.x) >= 117.8 and mm(p.y) <= 88.9 for p in pts) and not (t.GetClass() == "PCB_VIA" and abs(mm(t.GetX()) - 117.0) < 0.05):
        b.Delete(t); n += 1
print("removed", n)
p = {(r, q.GetNumber()): (mm(q.GetX()), mm(q.GetY())) for r, f in (("R44", r44), ("R45", r45)) for q in f.Pads()}
print(p)
def trk(net, w, pts):
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b); t.SetLayer(pcbnew.F_Cu); t.SetWidth(F(w)); t.SetStart(V(x1, y1)); t.SetEnd(V(x2, y2))
        t.SetNet(b.FindNet(net)); t.SetLocked(True); b.Add(t)
top = p[("R44", "1")]
trk("+5V", 0.3, [top, (122.35, top[1]), (122.35, 88.38), (117.86, 88.38), (117.0, 89.12)])
trk("HEATER_MID", 0.4, [p[("R44", "2")], p[("R45", "1")]])
lo = p[("R45", "2")]
trk("HEATER_LO", 0.3, [lo, (119.6, 87.9), (117.3, 87.9)])
pcbnew.SaveBoard("kicad/fc.kicad_pcb", b); print("saved")
