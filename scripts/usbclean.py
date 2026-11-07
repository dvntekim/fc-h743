"""Remove copper the autorouter added to USB nets that rev A did not have (redundant stubs)."""
import pcbnew
A = pcbnew.LoadBoard("/tmp/revA.kicad_pcb"); B = pcbnew.LoadBoard("kicad/fc.kicad_pcb"); mm = pcbnew.ToMM
def key(b, t):
    if t.GetClass() == "PCB_VIA": return ("v", round(mm(t.GetX()), 2), round(mm(t.GetY()), 2))
    a = (round(mm(t.GetStart().x), 2), round(mm(t.GetStart().y), 2)); c = (round(mm(t.GetEnd().x), 2), round(mm(t.GetEnd().y), 2))
    return (b.GetLayerName(t.GetLayer()), round(mm(t.GetWidth()), 3), min(a, c), max(a, c))
import sys
NETS = sys.argv[1:]
ka = {key(A, t) for t in A.GetTracks() if t.GetNetname() in NETS}
n = 0
for t in list(B.GetTracks()):
    if t.GetNetname() in NETS and key(B, t) not in ka: B.Delete(t); n += 1
pcbnew.SaveBoard("kicad/fc.kicad_pcb", B); print("removed", n)
