"""Widen the tracks of the given nets in place, as far as clearance allows.

For every segment, try the widths in WIDTHS (largest first, never narrower than now). A width is
accepted when the widened copper keeps the net-class clearance to every other-net pad, track,
via and non-GND pour on that layer, stays clear of keep-outs and holes, and stays inside the
0.55 mm edge ring. GND pours refill around the result afterwards.
Usage (chroot): python3 widen.py drc_last.json NET [NET ...]   env WIDTHS="1.2,1.0,0.8,0.6"
"""
import os, sys
nets = sys.argv[2:]
sys.argv = sys.argv[:2]
import fix_route as fr
import pcbnew
from shapely.geometry import LineString, Point, box

WIDTHS = [float(w) for w in os.environ.get("WIDTHS", "1.2,1.0,0.8,0.6,0.5").split(",")]
b = fr.b
EDGE = box(75.55, 75.55, 124.45, 124.45)
codes = {b.FindNet(n).GetNetCode(): n for n in nets}
changed = 0
for t in list(b.GetTracks()):
    if t.GetClass() == "PCB_VIA" or t.GetNetCode() not in codes or t.GetLayer() not in fr.SIG:
        continue
    l = t.GetLayer(); nc = t.GetNetCode(); cur = fr.tomm(t.GetWidth())
    ls = LineString([(fr.tomm(t.GetStart().x), fr.tomm(t.GetStart().y)), (fr.tomm(t.GetEnd().x), fr.tomm(t.GetEnd().y))])
    me = fr.net_clr(nc)
    for w in WIDTHS:
        if w <= cur + 1e-6:
            break
        g = ls.buffer(w / 2)
        if not EDGE.contains(g):
            continue
        ok = True
        for n2, l2, g2, obj in fr.ITEMS:
            if n2 == nc or l2 != l or n2 == 0:
                continue
            if g.distance(g2) < max(me, fr.net_clr(n2)) + 0.005:
                ok = False; break
        if ok:
            for h in fr.HOLES:
                if g.distance(h) < 0.25 and not any(n2 == nc and g2.contains(h.centroid) for n2, l2, g2, _ in fr.ITEMS if l2 == l):
                    ok = False; break
        if ok:
            for poly, lys, nt, nv in fr.KEEP:
                if nt and l in lys and poly.intersects(g):
                    ok = False; break
        if ok:
            t.SetWidth(fr.mm(w)); changed += 1
            # update the obstacle list so later segments see the wider copper
            for i, (n2, l2, g2, obj) in enumerate(fr.ITEMS):
                if obj is t:
                    fr.ITEMS[i] = (n2, l2, g, obj)
            break
pcbnew.SaveBoard(fr.PCB, b)
print("widened", changed, "segments of", ", ".join(nets))
