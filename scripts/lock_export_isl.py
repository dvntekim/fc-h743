"""Like lock_export.py, but tracks/vias inside the island and its approach (x 110-125, y 75-92.5)
stay unlocked so Freerouting may rip and re-route them; hand-placed island copper stays locked."""
import os, pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB); mm = pcbnew.ToMM
inr = lambda p: 117.0 <= mm(p.x) <= 125 and 75 <= mm(p.y) <= 90.6
n = 0
for t in b.GetTracks():
    if t.IsLocked():
        continue
    pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
    if all(inr(p) for p in pts) and t.GetNetname() != "GND":
        n += 1; continue
    t.SetLocked(True)
for z in list(b.Zones()):
    if not z.GetIsRuleArea() and z.GetNetname() == "GND" and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu):
        b.Remove(z)
print("unlocked", n, "dsn", pcbnew.ExportSpecctraDSN(b, os.path.join(HERE, "fc8.dsn")))
