import pcbnew
b=pcbnew.LoadBoard("kicad/fc.kicad_pcb"); mm=pcbnew.ToMM
for t in b.GetTracks():
    if t.GetClass()!="PCB_VIA": continue
    for f in b.GetFootprints():
        if f.GetReference() not in ("U20","U21","U22","U10"): continue
        for p in f.Pads():
            if p.HitTest(t.GetPosition()): print("via in pad", f.GetReference(), p.GetNumber(), t.GetNetname(), round(mm(t.GetX()),2), round(mm(t.GetY()),2))
