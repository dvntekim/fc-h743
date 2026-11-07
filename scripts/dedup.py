"""Remove zero-length and duplicate track segments (import leftovers)."""
import pcbnew
b = pcbnew.LoadBoard("kicad/fc.kicad_pcb"); mm = pcbnew.ToMM
seen = set(); n = 0
for t in list(b.GetTracks()):
    if t.GetClass() == "PCB_VIA":
        k = ("v", t.GetNetCode(), round(mm(t.GetX()), 3), round(mm(t.GetY()), 3))
    else:
        s, e = t.GetStart(), t.GetEnd()
        if (s - e).EuclideanNorm() < pcbnew.FromMM(0.02):
            b.Delete(t); n += 1; continue
        a, c = (round(mm(s.x), 3), round(mm(s.y), 3)), (round(mm(e.x), 3), round(mm(e.y), 3))
        k = ("t", t.GetNetCode(), t.GetLayer(), min(a, c), max(a, c))
    if k in seen:
        b.Delete(t); n += 1
    else:
        seen.add(k)
pcbnew.SaveBoard("kicad/fc.kicad_pcb", b); print("removed", n)
