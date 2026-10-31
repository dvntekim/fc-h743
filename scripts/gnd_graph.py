"""Own connectivity check for GND (KiCad's DRC reports pour islands only as zone pairs):
union-find over filled pour pieces, tracks, vias and pads; prints every component that is not
part of the main GND body, with its pads and bounding box."""
import os, sys, pcbnew
from shapely.geometry import Polygon, LineString, Point
from shapely.strtree import STRtree
PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
to = pcbnew.ToMM
NET = sys.argv[1] if len(sys.argv) > 1 else "GND"
nc = b.FindNet(NET).GetNetCode()
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]
items = []   # (layer, geom, label)
def poly(ol):
    return Polygon([(to(ol.CPoint(j).x), to(ol.CPoint(j).y)) for j in range(ol.PointCount())])
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetCode() != nc:
        continue
    for l in CU:
        if not z.IsOnLayer(l):
            continue
        fp = z.GetFilledPolysList(l)
        for i in range(fp.OutlineCount()):
            g = poly(fp.Outline(i))
            holes = [[(to(fp.Hole(i, h).CPoint(j).x), to(fp.Hole(i, h).CPoint(j).y)) for j in range(fp.Hole(i, h).PointCount())] for h in range(fp.HoleCount(i))]
            items.append((l, Polygon(g.exterior.coords, holes).buffer(0), f"zone {pcbnew.LayerName(l)}"))
for t in b.GetTracks():
    if t.GetNetCode() != nc:
        continue
    if t.GetClass() == "PCB_VIA":
        g = Point(to(t.GetPosition().x), to(t.GetPosition().y)).buffer(to(t.GetWidth(pcbnew.F_Cu)) / 2)
        for l in CU:
            items.append((l, g, "via"))
    else:
        g = LineString([(to(t.GetStart().x), to(t.GetStart().y)), (to(t.GetEnd().x), to(t.GetEnd().y))]).buffer(to(t.GetWidth()) / 2)
        items.append((t.GetLayer(), g, "track"))
for p in b.GetPads():
    if p.GetNetCode() != nc:
        continue
    lab = f"{p.GetParentFootprint().GetReference()}:{p.GetNumber()}"
    for l in CU:
        if p.IsOnLayer(l):
            sps = p.GetEffectivePolygon(l, pcbnew.ERROR_INSIDE)
            items.append((l, poly(sps.Outline(0)).buffer(0), "pad " + lab))
# vias / THT pads: tie all their per-layer pieces together
parent = list(range(len(items)))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i
def union(a, c):
    ra, rc = find(a), find(c)
    if ra != rc: parent[ra] = rc
groups = {}
for i, (l, g, lab) in enumerate(items):
    if lab in ("via",) or (lab.startswith("pad") and sum(1 for x in items if x[2] == lab) > 1):
        key = (lab, round(g.centroid.x, 3), round(g.centroid.y, 3))
        groups.setdefault(key, []).append(i)
for v in groups.values():
    for j in v[1:]:
        union(v[0], j)
for l in CU:
    idx = [i for i, it in enumerate(items) if it[0] == l]
    geoms = [items[i][1] for i in idx]
    tree = STRtree(geoms)
    for k, i in enumerate(idx):
        for m in tree.query(geoms[k]):
            if m > k and geoms[k].intersects(geoms[m]):
                union(i, idx[m])
comp = {}
for i in range(len(items)):
    comp.setdefault(find(i), []).append(i)
main = max(comp.values(), key=len)
for c in comp.values():
    if c is main:
        continue
    pads = sorted({items[i][2][4:] for i in c if items[i][2].startswith("pad")})
    if not pads and all(items[i][2].startswith("zone") for i in c):
        continue   # bare pour island without pads: harmless (KiCad removes or ignores it)
    xs = [items[i][1].bounds for i in c]
    bb = (min(x[0] for x in xs), min(x[1] for x in xs), max(x[2] for x in xs), max(x[3] for x in xs))
    print("ISOLATED", " ".join(pads) or "(tracks/vias only)", [round(v, 2) for v in bb], sorted({items[i][2] for i in c if not items[i][2].startswith("pad")}))
