"""Rework the 5 V buck layout so the switch node is a ~3 mm triangle (TPS54360B SW pin, catch
diode cathode, inductor pad) per the TI layout example, instead of a routed net.
 - rips all copper in the power corner (re-routed afterwards by Freerouting + finish passes)
 - U1 rotated so SW faces the inductor; D3 between U1 and L1; small parts re-placed on their pins
 - adds a BUCK_SW copper pour on F.Cu tying the three pads together."""
import os, math, pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
mm, tomm = pcbnew.FromMM, pcbnew.ToMM
RIP = (76.0, 101.5, 98.0, 119.0)
n = 0
for t in list(b.GetTracks()):
    pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
    if any(RIP[0] <= tomm(p.x) <= RIP[2] and RIP[1] <= tomm(p.y) <= RIP[3] for p in pts):
        b.Delete(t); n += 1
print("ripped", n)

def fp(r):
    return b.FindFootprintByReference(r)

def place(r, x, y, rot):
    f = fp(r); f.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); f.SetOrientationDegrees(rot)

L1 = fp("L1"); l1x, l1y = tomm(L1.GetPosition().x), tomm(L1.GetPosition().y)
place("U1", 85.8, 107.9, 270)
place("D3", 92.2, 110.55, 0)
place("L1", 91.6, 115.3, 0)

def court(f):
    lay = pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd
    f.BuildCourtyardCaches(); c = f.GetCourtyard(lay)
    if c.OutlineCount():
        bb = c.BBox()
    else:
        bb = f.GetBoundingBox(False, False)
    return (tomm(bb.GetX()), tomm(bb.GetY()), tomm(bb.GetRight()), tomm(bb.GetBottom()))

def ov(a, c, g=0.0):
    return a[0] < c[2] + g and a[2] + g > c[0] and a[1] < c[3] + g and a[3] + g > c[1]

HOLES = [(84.75, 84.75), (115.25, 84.75), (84.75, 115.25), (115.25, 115.25)]
def ok_board(bb):
    if bb[0] < 75.3 or bb[2] > 124.7 or bb[1] < 75.3 or bb[3] > 124.7:
        return False
    for hx, hy in HOLES:
        dx = max(bb[0] - hx, 0, hx - bb[2]); dy = max(bb[1] - hy, 0, hy - bb[3])
        if math.hypot(dx, dy) < 3.05:
            return False
    return True

def pad_xy(r, num):
    p = next(p for p in fp(r).Pads() if p.GetNumber() == num).GetPosition()
    return tomm(p.x), tomm(p.y)

MOVE = [("C9", "U1", "1"), ("C6", "U1", "2"), ("C7", "U1", "2"), ("C8", "U1", "2"),
        ("R5", "U1", "3"), ("R6", "U1", "3"), ("R7", "U1", "4"), ("R8", "U1", "5"), ("R9", "U1", "5"),
        ("R10", "U1", "6"), ("C14", "U1", "6"), ("C15", "U1", "6"),
        ("C10", "L1", "2"), ("C11", "L1", "2"), ("C13", "L1", "2"), ("R2", "C7", "1")]
moving = {r for r, _, _ in MOVE}
fixed_now = {"U1", "D3", "L1"}
side_of = lambda f: "bot" if f.IsFlipped() else "top"
placed = []
for f in b.GetFootprints():
    if f.GetReference() not in moving and side_of(f) == "top":
        placed.append((f.GetReference(), court(f)))
# anything (other than the movers) that now collides with U1/D3 also moves
for f in b.GetFootprints():
    r = f.GetReference()
    if r in moving or r in fixed_now or side_of(f) != "top" or r.startswith(("H", "FID", "U", "J", "Q")):
        continue
    if any(ov(court(f), court(fp(x))) for x in ("U1", "D3")):
        p = f.GetPosition(); MOVE.append((r, None, (tomm(p.x), tomm(p.y)))); moving.add(r)
        placed = [(rr, bb) for rr, bb in placed if rr != r]
        print("displaced", r)
for r, aref, apad in MOVE:
    f = fp(r)
    tx, ty = pad_xy(aref, apad) if aref else apad
    best = None
    for rad in [i * 0.2 for i in range(0, 60)]:
        k = max(1, int(2 * math.pi * rad / 0.3))
        for j in range(k):
            a = 2 * math.pi * j / k
            for rot in (0, 90):
                f.SetPosition(pcbnew.VECTOR2I(mm(round((tx + rad * math.cos(a)) / 0.05) * 0.05), mm(round((ty + rad * math.sin(a)) / 0.05) * 0.05)))
                f.SetOrientationDegrees(rot)
                bb = court(f)
                if ok_board(bb) and not any(ov(bb, o) for rr, o in placed if rr != r):
                    best = True; break
            if best: break
        if best: break
    if not best:
        print("could not place", r)
    placed.append((r, court(f)))
    print("placed", r, round(tomm(f.GetPosition().x), 2), round(tomm(f.GetPosition().y), 2), f.GetOrientationDegrees())

for a_ in ("U1", "D3", "L1"):
    for rr, o in placed:
        if rr not in ("U1", "D3", "L1") and ov(court(fp(a_)), o):
            print("OVERLAP", a_, rr)
# switch-node pour: hull of U1.8, D3.1, L1.1 pads
from shapely.geometry import Polygon, MultiPoint
pts = []
for r, num in (("U1", "8"), ("D3", "1"), ("L1", "1")):
    p = next(p for p in fp(r).Pads() if p.GetNumber() == num)
    sps = p.GetEffectivePolygon(pcbnew.F_Cu, pcbnew.ERROR_INSIDE); ol = sps.Outline(0)
    pts += [(tomm(ol.CPoint(j).x), tomm(ol.CPoint(j).y)) for j in range(ol.PointCount())]
hull = MultiPoint(pts).convex_hull
z = pcbnew.ZONE(b); z.SetLayer(pcbnew.F_Cu); z.SetNet(b.FindNet("BUCK_SW"))
ol = pcbnew.SHAPE_POLY_SET(); ol.NewOutline()
for x, y in list(hull.exterior.coords)[:-1]:
    ol.Append(mm(x), mm(y))
ol.thisown = 0; z.SetOutline(ol)
z.SetAssignedPriority(10); z.SetLocalClearance(mm(0.2)); z.SetMinThickness(mm(0.25))
z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL); z.SetZoneName("SW node")
b.Add(z)
print("SW pour area mm2", round(hull.area, 1))
pcbnew.SaveBoard(PCB, b)
