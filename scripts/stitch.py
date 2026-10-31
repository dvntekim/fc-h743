"""GND stitching for the routed board.
  python3 stitch.py grid          -> GND via fence/grid wherever a via fits on every layer
  python3 stitch.py pads R1:2 ... -> a dedicated GND via + short track for the listed pads
  python3 stitch.py pads-auto drc.json -> same, for every GND pad DRC reports as unconnected
Obstacles = all non-GND copper on every layer, every hole, the board edge."""
import os, sys, json, math, pcbnew
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
mm, tomm = pcbnew.FromMM, pcbnew.ToMM
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]
SIG = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.B_Cu]
GND = b.FindNet("GND")
VIA_D, VIA_DRILL = float(os.environ.get("VIA_D", "0.45")), float(os.environ.get("VIA_DR", "0.2"))
X0, Y0, X1, Y1 = 75.0, 75.0, 125.0, 125.0

def poly_of(sps):
    out = []
    for i in range(sps.OutlineCount()):
        ol = sps.Outline(i)
        pts = [(tomm(ol.CPoint(j).x), tomm(ol.CPoint(j).y)) for j in range(ol.PointCount())]
        if len(pts) >= 3:
            out.append(Polygon(pts).buffer(0))
    return unary_union(out)

def build(include_gnd_pads):
    """per-layer obstacle geometry"""
    obs = {l: [] for l in CU}
    holes = []
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            is_gnd = pad.GetNetCode() == GND.GetNetCode()
            if pad.HasHole():
                holes.append(Point(tomm(pad.GetPosition().x), tomm(pad.GetPosition().y)).buffer(tomm(pad.GetDrillSize().x) / 2))
            if is_gnd and not include_gnd_pads:
                continue
            for l in CU:
                if pad.IsOnLayer(l) and pad.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                    obs[l].append((poly_of(pad.GetEffectivePolygon(l, pcbnew.ERROR_INSIDE)), is_gnd))
    for t in b.GetTracks():
        is_gnd = t.GetNetCode() == GND.GetNetCode()
        if t.GetClass() == "PCB_VIA":
            p = Point(tomm(t.GetPosition().x), tomm(t.GetPosition().y))
            holes.append(p.buffer(tomm(t.GetDrill()) / 2))
            if is_gnd:
                continue
            for l in CU:
                obs[l].append((p.buffer(tomm(t.GetWidth(pcbnew.F_Cu)) / 2), False))
        else:
            if is_gnd:
                continue
            ls = LineString([(tomm(t.GetStart().x), tomm(t.GetStart().y)), (tomm(t.GetEnd().x), tomm(t.GetEnd().y))])
            obs[t.GetLayer()].append((ls.buffer(tomm(t.GetWidth()) / 2), False))
    # rule areas that forbid vias (board-level and footprint keepouts, e.g. under the microSD)
    zs = list(b.Zones()) + [z for fp in b.GetFootprints() for z in fp.Zones()]
    for z in zs:
        if z.GetIsRuleArea() and z.GetDoNotAllowVias():
            g = poly_of(z.Outline())
            for l in CU:
                if z.IsOnLayer(l):
                    obs[l].append((g, False))
    trees = {}
    for l in CU:
        geoms = [g for g, _ in obs[l]]
        trees[l] = (STRtree(geoms), geoms, [f for _, f in obs[l]])
    return trees, STRtree(holes) if holes else None, holes

def clear(trees, layer, geom, clr, ignore_gnd=False):
    tree, geoms, flags = trees[layer]
    for i in tree.query(geom.buffer(clr)):
        if ignore_gnd and flags[i]:
            continue
        if geoms[i].distance(geom) < clr:
            return False
    return True

def hole_ok(htree, holes, p, min_d):
    if htree is None:
        return True
    for i in htree.query(p.buffer(min_d + 2)):
        if holes[i].distance(p) < min_d:
            return False
    return True

def add_via(x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DRILL)); v.SetNet(GND)
    b.Add(v)

def add_track(a, c, layer, w):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1]))); t.SetEnd(pcbnew.VECTOR2I(mm(c[0]), mm(c[1])))
    t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNet(GND)
    b.Add(t)

def save():
    pcbnew.SaveBoard(PCB, b)

mode = sys.argv[1]
if mode == "grid":
    trees, htree, holes = build(include_gnd_pads=True)
    edge = box(X0 + 0.8, Y0 + 0.8, X1 - 0.8, Y1 - 0.8)
    pitch = float(os.environ.get("PITCH", "2.0"))
    n = 0
    placed = []
    y = Y0 + 1.0
    while y < Y1 - 0.9:
        x = X0 + 1.0
        while x < X1 - 0.9:
            p = Point(x, y)
            c = p.buffer(VIA_D / 2)
            if edge.contains(c) and hole_ok(htree, holes, p, VIA_DRILL / 2 + 0.35) \
                    and all(clear(trees, l, c, 0.25) for l in CU if l not in (pcbnew.In1_Cu, pcbnew.In4_Cu)) \
                    and all(math.hypot(x - a, y - bb) > 0.9 for a, bb in placed[-200:]):
                add_via(x, y); placed.append((x, y)); n += 1
            x += pitch
        y += pitch
    save(); print("grid vias", n)
elif mode == "vip":
    # via-in-pad (JLC 6-layer: epoxy-filled and capped) for GND pads with no room for an escape via
    trees, htree, holes = build(include_gnd_pads=False)
    n = 0
    for a in sys.argv[2:]:
        ref, num = a.split(":")
        fp = b.FindFootprintByReference(ref)
        pad = next(p for p in fp.Pads() if p.GetNumber() == num)
        x, y = tomm(pad.GetPosition().x), tomm(pad.GetPosition().y)
        p = Point(x, y); c = p.buffer(VIA_D / 2)
        if hole_ok(htree, holes, p, VIA_DRILL / 2 + 0.3) and all(clear(trees, l, c, 0.11) for l in CU):
            add_via(x, y); n += 1
            holes.append(p.buffer(VIA_DRILL / 2)); htree = STRtree(holes)
        else:
            print("vip blocked", ref, num)
    save(); print("via-in-pad", n, "of", len(sys.argv) - 2)
else:
    if mode == "pads-auto":
        d = json.load(open(sys.argv[2]))
        want = set()
        for u in d["unconnected_items"]:
            for it in u["items"]:
                desc = it["description"]
                if desc.startswith("Pad ") and "[GND]" in desc:
                    num = desc.split()[1]; ref = desc.split(" of ")[1].split()[0]
                    want.add((ref, num))
    else:
        want = {tuple(a.split(":")) for a in sys.argv[2:]}
    trees, htree, holes = build(include_gnd_pads=False)
    done = 0
    for ref, num in sorted(want):
        fp = b.FindFootprintByReference(ref)
        pad = next(p for p in fp.Pads() if p.GetNumber() == num)
        layer = pcbnew.B_Cu if pad.IsOnLayer(pcbnew.B_Cu) and not pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.F_Cu
        px, py = tomm(pad.GetPosition().x), tomm(pad.GetPosition().y)
        best = None
        for r in [0.6 + 0.1 * k for k in range(18)]:
            for k in range(24):
                a = 2 * math.pi * k / 24
                x, y = px + r * math.cos(a), py + r * math.sin(a)
                p = Point(x, y); c = p.buffer(VIA_D / 2)
                if not box(X0 + 0.8, Y0 + 0.8, X1 - 0.8, Y1 - 0.8).contains(c):
                    continue
                if not hole_ok(htree, holes, p, VIA_DRILL / 2 + 0.3):
                    continue
                if not all(clear(trees, l, c, 0.15) for l in CU):
                    continue
                if not clear(trees, layer, LineString([(px, py), (x, y)]).buffer(0.125), 0.12):
                    continue
                best = (x, y); break
            if best:
                break
        if best:
            add_via(*best); add_track((px, py), best, layer, 0.25)
            trees[pcbnew.F_Cu]  # obstacles of other nets unchanged; GND additions are fine
            done += 1
        else:
            print("no room for", ref, num)
    save(); print("pad vias", done, "of", len(want))
