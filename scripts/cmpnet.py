import pcbnew, sys
A = pcbnew.LoadBoard("/tmp/revA.kicad_pcb"); B = pcbnew.LoadBoard("kicad/fc.kicad_pcb"); mm = pcbnew.ToMM
def segs(b, n):
    s = set()
    for t in b.GetTracks():
        if t.GetNetname() == n:
            if t.GetClass() == "PCB_VIA": s.add(("v", round(mm(t.GetX()), 2), round(mm(t.GetY()), 2)))
            else:
                a = (round(mm(t.GetStart().x), 2), round(mm(t.GetStart().y), 2)); c = (round(mm(t.GetEnd().x), 2), round(mm(t.GetEnd().y), 2))
                s.add((b.GetLayerName(t.GetLayer()), round(mm(t.GetWidth()), 3), min(a, c), max(a, c)))
    return s
for n in sys.argv[1:]:
    a, c = segs(A, n), segs(B, n)
    print(n, "revA", len(a), "revB", len(c), "only A", sorted(a - c)[:6], "only B", sorted(c - a)[:6])
