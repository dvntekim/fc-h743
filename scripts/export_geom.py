"""Dump copper geometry of the routed board to JSON for the IR-drop and thermal solvers.
Runs in KiCad's Python: tracks, arcs (as chords), filled zones, pad polygons, vias, footprint
positions. Output: out/geom.json"""
import json, os, pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
b = pcbnew.LoadBoard(os.path.join(HERE, "kicad", "fc.kicad_pcb"))
mm = pcbnew.ToMM
CU = {pcbnew.F_Cu: "F", pcbnew.In1_Cu: "In1", pcbnew.In2_Cu: "In2", pcbnew.In3_Cu: "In3",
      pcbnew.In4_Cu: "In4", pcbnew.B_Cu: "B"}


def poly(sps):
    out = []
    for i in range(sps.OutlineCount()):
        ol = sps.Outline(i)
        holes = []
        for h in range(sps.HoleCount(i)):
            hl = sps.Hole(i, h)
            holes.append([(mm(hl.CPoint(j).x), mm(hl.CPoint(j).y)) for j in range(hl.PointCount())])
        out.append([[(mm(ol.CPoint(j).x), mm(ol.CPoint(j).y)) for j in range(ol.PointCount())], holes])
    return out


g = {"tracks": [], "vias": [], "zones": [], "pads": [], "fps": []}
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        g["vias"].append(dict(x=mm(t.GetX()), y=mm(t.GetY()), d=mm(t.GetWidth(pcbnew.F_Cu)),
                              drill=mm(t.GetDrillValue()), net=t.GetNetname()))
    elif t.GetLayer() in CU:
        g["tracks"].append(dict(l=CU[t.GetLayer()], net=t.GetNetname(), w=mm(t.GetWidth()),
                                x1=mm(t.GetStart().x), y1=mm(t.GetStart().y),
                                x2=mm(t.GetEnd().x), y2=mm(t.GetEnd().y)))
for z in b.Zones():
    if z.GetIsRuleArea():
        continue
    for lid, ln in CU.items():
        if z.IsOnLayer(lid):
            fp = z.GetFilledPolysList(lid)
            if fp.OutlineCount():
                g["zones"].append(dict(l=ln, net=z.GetNetname(), polys=poly(fp)))
for f in b.GetFootprints():
    g["fps"].append(dict(ref=f.GetReference(), value=f.GetValue(), x=mm(f.GetX()), y=mm(f.GetY()),
                         side="B" if f.IsFlipped() else "F"))
    for p in f.Pads():
        for lid, ln in CU.items():
            if p.IsOnLayer(lid) and p.IsOnCopperLayer():
                sps = p.GetEffectivePolygon(lid, pcbnew.ERROR_INSIDE)
                g["pads"].append(dict(ref=f.GetReference(), pad=p.GetNumber(), l=ln, net=p.GetNetname(),
                                      x=mm(p.GetX()), y=mm(p.GetY()),
                                      drill=mm(p.GetDrillSize().x) if p.HasHole() else 0,
                                      polys=poly(sps)))
os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
json.dump(g, open(os.path.join(HERE, "out", "geom.json"), "w"))
print("tracks", len(g["tracks"]), "vias", len(g["vias"]), "zones", len(g["zones"]), "pads", len(g["pads"]))
