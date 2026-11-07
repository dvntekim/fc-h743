import pcbnew
from shapely.geometry import LineString
b=pcbnew.LoadBoard("kicad/fc.kicad_pcb"); mm=pcbnew.ToMM
cut=LineString([(118.5,86.7),(121.1,89.5)])
res={}
for t in b.GetTracks():
    if t.GetClass()=="PCB_VIA": continue
    s=LineString([(mm(t.GetStart().x),mm(t.GetStart().y)),(mm(t.GetEnd().x),mm(t.GetEnd().y))])
    if s.intersects(cut):
        res.setdefault(b.GetLayerName(t.GetLayer()),set()).add((t.GetNetname(),round(mm(t.GetWidth()),2)))
for k,v in res.items(): print(k,len(v),sorted(v))
print("cut length", cut.length)
