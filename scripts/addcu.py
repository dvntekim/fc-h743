"""addcu.py SPEC... : add copper. SPEC = t:NET:LAYER:W:x1,y1;x2,y2;...  or v:NET:x,y  or d:NET:LAYER:x,y (delete tracks of NET on LAYER touching x,y)"""
import sys, pcbnew
b = pcbnew.LoadBoard("kicad/fc.kicad_pcb"); F = pcbnew.FromMM; V = lambda x, y: pcbnew.VECTOR2I(F(x), F(y)); mm = pcbnew.ToMM
L = {"F": pcbnew.F_Cu, "In2": pcbnew.In2_Cu, "In3": pcbnew.In3_Cu, "B": pcbnew.B_Cu}
for s in sys.argv[1:]:
    k = s.split(":")
    if k[0] == "t":
        pts = [tuple(map(float, p.split(","))) for p in k[4].split("/")]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b); t.SetLayer(L[k[2]]); t.SetWidth(F(float(k[3]))); t.SetStart(V(x1, y1)); t.SetEnd(V(x2, y2))
            t.SetNet(b.FindNet(k[1])); t.SetLocked(True); b.Add(t)
    elif k[0] == "v":
        x, y = map(float, k[2].split(","))
        d, dr = (float(k[3]), float(k[4])) if len(k) > 4 else (0.45, 0.2)
        v = pcbnew.PCB_VIA(b); v.SetPosition(V(x, y)); v.SetWidth(F(d)); v.SetDrill(F(dr)); v.SetNet(b.FindNet(k[1])); v.SetLocked(True); b.Add(v)
    elif k[0] == "d":
        x, y = map(float, k[3].split(","))
        for t in list(b.GetTracks()):
            if t.GetNetname() != k[1]: continue
            if t.GetClass() == "PCB_VIA":
                if k[2] == "via" and abs(mm(t.GetX()) - x) < 0.02 and abs(mm(t.GetY()) - y) < 0.02: b.Delete(t); print("del via")
                continue
            if k[2] == "via" or (k[2] != "*" and t.GetLayer() != L[k[2]]): continue
            if any(abs(mm(p.x) - x) < 0.02 and abs(mm(p.y) - y) < 0.02 for p in (t.GetStart(), t.GetEnd())): b.Delete(t); print("del trk")
pcbnew.SaveBoard("kicad/fc.kicad_pcb", b); print("ok")
