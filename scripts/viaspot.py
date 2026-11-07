"""viaspot.py x0 y0 x1 y1 [net]: grid points where a 0.45/0.2 via clears every non-<net> item on all layers by 0.11."""
import sys, pcbnew
from shapely.geometry import Point, LineString, Polygon
b = pcbnew.LoadBoard("kicad/fc.kicad_pcb"); mm = pcbnew.ToMM
x0, y0, x1, y1 = map(float, sys.argv[1:5]); net = sys.argv[5] if len(sys.argv) > 5 else ""
G = []
for t in b.GetTracks():
    if t.GetNetname() == net or (t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND" and len(sys.argv) > 6): continue
    if t.GetClass() == "PCB_VIA":
        G.append(Point(mm(t.GetX()), mm(t.GetY())).buffer(mm(t.GetWidth(pcbnew.F_Cu)) / 2))
    else:
        G.append(LineString([(mm(t.GetStart().x), mm(t.GetStart().y)), (mm(t.GetEnd().x), mm(t.GetEnd().y))]).buffer(mm(t.GetWidth()) / 2))
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname() == net and net: continue
        bb = p.GetBoundingBox()
        G.append(Polygon([(mm(bb.GetLeft()), mm(bb.GetTop())), (mm(bb.GetRight()), mm(bb.GetTop())), (mm(bb.GetRight()), mm(bb.GetBottom())), (mm(bb.GetLeft()), mm(bb.GetBottom()))]))
for z in b.Zones():
    if z.GetIsRuleArea():
        o = z.Outline().Outline(0)
        G.append(Polygon([(mm(o.CPoint(i).x), mm(o.CPoint(i).y)) for i in range(o.PointCount())]))
G.append(Point(115.25, 84.75).buffer(2.4))
from shapely.strtree import STRtree
T = STRtree(G)
y = y0
while y <= y1:
    x = x0
    row = []
    while x <= x1:
        import os; c = Point(x, y).buffer(float(os.environ.get("VR", "0.225")) + 0.11)
        if not any(G[i].intersects(c) for i in T.query(c)):
            row.append(round(x, 2))
        x += 0.1
    if row: print(round(y, 2), row)
    y += 0.1
