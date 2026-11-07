import pcbnew, math
b=pcbnew.LoadBoard("kicad/fc.kicad_pcb"); mm=pcbnew.ToMM
holes=[(f.GetReference(),mm(p.GetX()),mm(p.GetY()),mm(p.GetDrillSize().x)) for f in b.GetFootprints() for p in f.Pads() if p.GetAttribute()==pcbnew.PAD_ATTRIB_NPTH]
print("NPTH:",holes)
vias=[t for t in b.GetTracks() if t.GetClass()=="PCB_VIA"]
for ref,x,y,d in holes:
    for v in vias:
        e=math.dist((mm(v.GetX()),mm(v.GetY())),(x,y))-d/2-mm(v.GetDrillValue())/2
        if e<3.0: print(f"  via {v.GetNetname()} at ({mm(v.GetX()):.2f},{mm(v.GetY()):.2f}) hole-edge gap {e:.2f} mm to {ref} ({d} mm)")
# via copper to other pads (any net) closer than 0.1
from shapely.geometry import Point, Polygon
def poly(p,l):
    s=p.GetEffectivePolygon(l,pcbnew.ERROR_INSIDE); o=s.Outline(0)
    return Polygon([(mm(o.CPoint(i).x),mm(o.CPoint(i).y)) for i in range(o.PointCount())])
n=0
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetAttribute()!=pcbnew.PAD_ATTRIB_SMD: continue
        l=pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
        pg=poly(p,l)
        for v in vias:
            g=Point(mm(v.GetX()),mm(v.GetY())).buffer(mm(v.GetWidth(l))/2)
            d=pg.distance(g)
            if d<0.1 and not pg.contains(g.centroid):
                n+=1; print(f"  pad {f.GetReference()}.{p.GetNumber()} ({p.GetNetname()}) via {v.GetNetname()} gap {d:.3f} {'SAME' if p.GetNetCode()==v.GetNetCode() else 'DIFF'}")
print("via-pad <0.1:",n)
