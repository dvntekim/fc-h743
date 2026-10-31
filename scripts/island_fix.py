"""Tie floating GND pour islands to the planes: any filled GND island (on any layer) that holds
no GND via or through-hole GND pad gets a stitching via placed inside it, where the via clears
every other net on all layers. Islands that cannot take a via are reported.
Usage (chroot): python3 island_fix.py"""
import os, sys, math
import pcbnew
from shapely.geometry import Point, Polygon
from shapely.prepared import prep
sys.argv = [sys.argv[0], os.path.join(os.path.dirname(os.path.abspath(__file__)), "drc_last.json")]
import fix_route as fr   # obstacles + helpers (also drops keepout vias)

b = fr.b
mm, tomm = pcbnew.FromMM, pcbnew.ToMM
GND = b.FindNet("GND").GetNetCode()
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]
anchors = []
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA" and t.GetNetCode() == GND:
        anchors.append(Point(tomm(t.GetPosition().x), tomm(t.GetPosition().y)))
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.HasHole() and p.GetNetCode() == GND:
            anchors.append(Point(tomm(p.GetPosition().x), tomm(p.GetPosition().y)))

def via_ok(x, y):
    c = Point(x, y)
    for n, l, g, _ in fr.ITEMS:
        if n == GND:
            continue
        if g.distance(c) < fr.VIA_D / 2 + max(0.12, fr.net_clr(n) + 0.01):
            return False
    for h in fr.HOLES:
        if h.distance(c) < fr.VIA_DR / 2 + 0.3:
            return False
    for p, ls, nt, nv in fr.KEEP:
        if nv and p.distance(c) < fr.VIA_D / 2 + 0.05:
            return False
    return 75.9 < x < 124.1 and 75.9 < y < 124.1

added = failed = 0
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetCode() != GND:
        continue
    l = z.GetLayer()
    fp = z.GetFilledPolysList(l)
    for i in range(fp.OutlineCount()):
        ol = fp.Outline(i)
        poly = Polygon([(tomm(ol.CPoint(j).x), tomm(ol.CPoint(j).y)) for j in range(ol.PointCount())])
        holes = []
        for h in range(fp.HoleCount(i)):
            hh = fp.Hole(i, h)
            holes.append([(tomm(hh.CPoint(j).x), tomm(hh.CPoint(j).y)) for j in range(hh.PointCount())])
        poly = Polygon(poly.exterior.coords, holes).buffer(0)
        if poly.area < 0.05:
            continue
        pp = prep(poly.buffer(0.05))
        if any(pp.contains(a) for a in anchors):
            continue
        inner = poly.buffer(-(fr.VIA_D / 2 + 0.02))
        if inner.is_empty:
            inner = poly.buffer(-0.01)
        x0, y0, x1, y1 = inner.bounds
        pi = prep(inner)
        cands = []
        k = 0.1
        y = y0
        while y <= y1:
            x = x0
            while x <= x1:
                if pi.contains(Point(x, y)):
                    cands.append((inner.boundary.distance(Point(x, y)), x, y))
                x += k
            y += k
        cands.sort(reverse=True)
        spot = next(((x, y) for _, x, y in cands if via_ok(x, y)), None)
        if spot is None:
            # no room for a via: run a track from the island to the nearest GND anchor
            rp = poly.representative_point()
            tg = sorted(anchors, key=lambda a: a.distance(rp))[:4]
            done_ = False
            if l in fr.SIG:
                for a_ in tg:
                    for w in (0.2, 0.15, 0.127):
                        pts = fr.route(GND, (rp.x, rp.y), [l], (a_.x, a_.y), fr.SIG, w)
                        if pts:
                            fr.emit(GND, pts, w); done_ = True; break
                    if done_:
                        break
            if done_:
                print("island tied by track", pcbnew.LayerName(l)); added += 1
            else:
                print("no via spot", pcbnew.LayerName(l), [round(v, 2) for v in poly.bounds]); failed += 1
            continue
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(mm(spot[0]), mm(spot[1]))); v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetWidth(mm(fr.VIA_D)); v.SetDrill(mm(fr.VIA_DR)); v.SetNet(b.FindNet(GND))
        b.Add(v)
        p = Point(*spot); anchors.append(p)
        for ll in fr.SIG:
            fr.ITEMS.append((GND, ll, p.buffer(fr.VIA_D / 2), v))
        fr.HOLES.append(p.buffer(fr.VIA_DR / 2))
        added += 1
pcbnew.SaveBoard(fr.PCB, b)
print("island vias", added, "unfixed", failed)
