import os, pcbnew
b = pcbnew.LoadBoard("kicad/fc.kicad_pcb"); mm = pcbnew.ToMM
inr = lambda p: 117.0 <= mm(p.x) <= 125 and 75 <= mm(p.y) <= 90.6
n = 0
for t in list(b.GetTracks()):
    if t.IsLocked(): continue
    pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
    if all(inr(p) for p in pts) and t.GetNetname() != "GND":
        b.Delete(t); n += 1
pcbnew.SaveBoard("kicad/fc.kicad_pcb", b); print("deleted", n)
