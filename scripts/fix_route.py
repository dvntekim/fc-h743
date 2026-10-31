"""Finish the connections Freerouting left open (from KiCad's DRC report) with a local grid A*
on the four signal layers. Each connection is routed inside a window around its two ends with
full clearance to every other net's copper, holes and keepouts.
Usage (chroot): python3 fix_route.py drc_last.json [NET ...]"""
import os, sys, json, math, heapq
import numpy as np
import pcbnew
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
mm, tomm = pcbnew.FromMM, pcbnew.ToMM
SIG = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.B_Cu]
LNAME = {pcbnew.F_Cu: "F.Cu", pcbnew.In2_Cu: "In2.Cu", pcbnew.In3_Cu: "In3.Cu", pcbnew.B_Cu: "B.Cu"}
BYNAME = {v: k for k, v in LNAME.items()}
RES = 0.025
M = float(os.environ.get("MARGIN", "3.0"))
CLR = float(os.environ.get("CLR", "0.13"))
VIA_D, VIA_DR = float(os.environ.get("VIA_D", "0.45")), float(os.environ.get("VIA_DR", "0.2"))
WIDTH = {"VBAT": 0.4, "+3V3": 0.3, "+5V_PERIPH": 0.4, "+5V": 0.4, "+5V_FMU": 0.4, "GND": 0.3}

def poly_of(sps):
    out = []
    for i in range(sps.OutlineCount()):
        ol = sps.Outline(i)
        pts = [(tomm(ol.CPoint(j).x), tomm(ol.CPoint(j).y)) for j in range(ol.PointCount())]
        if len(pts) >= 3:
            out.append(Polygon(pts).buffer(0))
    return unary_union(out)

def copper_items():
    """(netcode, layer, geometry) for every copper item; layer None = all copper layers (holes)"""
    items, holes = [], []
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.HasHole():
                holes.append(Point(tomm(pad.GetPosition().x), tomm(pad.GetPosition().y)).buffer(tomm(pad.GetDrillSize().x) / 2))
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue
            for l in SIG:
                if pad.IsOnLayer(l):
                    items.append((pad.GetNetCode(), l, poly_of(pad.GetEffectivePolygon(l, pcbnew.ERROR_INSIDE)), pad))
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            p = Point(tomm(t.GetPosition().x), tomm(t.GetPosition().y))
            holes.append(p.buffer(tomm(t.GetDrill()) / 2))
            for l in SIG:
                items.append((t.GetNetCode(), l, p.buffer(tomm(t.GetWidth(pcbnew.F_Cu)) / 2), t))
        else:
            if t.GetLayer() not in SIG:
                continue
            ls = LineString([(tomm(t.GetStart().x), tomm(t.GetStart().y)), (tomm(t.GetEnd().x), tomm(t.GetEnd().y))])
            items.append((t.GetNetCode(), t.GetLayer(), ls.buffer(tomm(t.GetWidth()) / 2), t))
    # non-GND copper pours (switch node, VIN) are obstacles for other nets
    for z in b.Zones():
        if z.GetIsRuleArea() or z.GetNetname() == "GND":
            continue
        for l in SIG:
            if z.IsOnLayer(l):
                items.append((z.GetNetCode(), l, poly_of(z.Outline()), None))
    keep = []
    for z in list(b.Zones()) + [z for fp in b.GetFootprints() for z in fp.Zones()]:
        if z.GetIsRuleArea() and (z.GetDoNotAllowTracks() or z.GetDoNotAllowVias()):
            keep.append((poly_of(z.Outline()), [l for l in SIG if z.IsOnLayer(l)], z.GetDoNotAllowTracks(), z.GetDoNotAllowVias()))
    return items, holes, keep

# drop vias DRC found inside keepouts
_d = json.load(open(sys.argv[1]))
for v in _d["violations"]:
    if v["type"] == "items_not_allowed":
        for i in v["items"]:
            if i["description"].startswith("Via"):
                for t in list(b.GetTracks()):
                    if t.GetClass() == "PCB_VIA" and abs(tomm(t.GetPosition().x) - i["pos"]["x"]) < 0.01 \
                            and abs(tomm(t.GetPosition().y) - i["pos"]["y"]) < 0.01:
                        b.Delete(t); print("removed keepout via", i["pos"])
ITEMS, HOLES, KEEP = copper_items()
import fnmatch
_nc = json.load(open(os.path.join(HERE, "netclasses.json")))
_clr = {c["name"]: c["clearance"] for c in _nc["classes"]}
_pat = [(p["pattern"], p["netclass"]) for p in _nc["netclass_patterns"]]
_cache = {}
def net_class(name):
    return next((c for pt, c in _pat if fnmatch.fnmatchcase(name, pt)), "Default")
_tw = {c["name"]: c["track_width"] for c in _nc["classes"]}
_minw = {"HighCurrent": 0.5, "Power": 0.3, "Supply": 0.2, "GND": 0.2}
def widths_for(name):
    cls = net_class(name); w0 = _tw.get(cls, 0.127); mn = _minw.get(cls, 0.127)
    return [w for w in (w0, 0.6, 0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.127) if mn <= w <= w0]
def net_clr(code):
    if code not in _cache:
        name = b.FindNet(code).GetNetname() if b.FindNet(code) else ""
        cls = next((c for pt, c in _pat if fnmatch.fnmatchcase(name, pt)), "Default")
        _cache[code] = _clr.get(cls, 0.1)
    return _cache[code]

def raster(geoms, x0, y0, nx, ny):
    im = Image.new("1", (nx, ny), 0)
    d = ImageDraw.Draw(im)
    def draw(g):
        if g.is_empty:
            return
        if g.geom_type == "Polygon":
            d.polygon([((x - x0) / RES, (y - y0) / RES) for x, y in g.exterior.coords], fill=1)
            for h in g.interiors:
                d.polygon([((x - x0) / RES, (y - y0) / RES) for x, y in h.coords], fill=0)
        elif hasattr(g, "geoms"):
            for gg in g.geoms:
                draw(gg)
    for g in geoms:
        draw(g)
    return np.array(im, dtype=bool)

def route(netcode, a, alayers, c, clayers, w):
    x0 = min(a[0], c[0]) - M; y0 = min(a[1], c[1]) - M
    x1 = max(a[0], c[0]) + M; y1 = max(a[1], c[1]) + M
    nx, ny = int((x1 - x0) / RES) + 1, int((y1 - y0) / RES) + 1
    win = box(x0, y0, x1, y1)
    blocked, viablk = [], None
    for l in SIG:
        gs = [g.buffer(max(CLR, net_clr(n) + 0.01, net_clr(netcode) + 0.01) + w / 2) for n, ll, g, _ in ITEMS
              if ll == l and n != netcode and g.intersects(win.buffer(1))]
        gs += [h.buffer(0.22 + w / 2) for h in HOLES if h.intersects(win.buffer(1))]
        gs += [p.buffer(w / 2 + 0.02) for p, ls, nt, nv in KEEP if nt and l in ls]
        gs.append(win.difference(box(75.5, 75.5, 124.5, 124.5)))
        blocked.append(raster(gs, x0, y0, nx, ny))
    vr = VIA_D / 2
    vg = []
    for l in SIG:
        vg += [g.buffer(max(CLR, net_clr(n) + 0.01, net_clr(netcode) + 0.01) + vr) for n, ll, g, _ in ITEMS
               if ll == l and n != netcode and g.intersects(win.buffer(1))]
    vg += [h.buffer(0.3 + VIA_DR / 2) for h in HOLES if h.intersects(win.buffer(1))]
    vg += [p.buffer(vr + 0.02) for p, ls, nt, nv in KEEP if nv]
    viablk = raster(vg, x0, y0, nx, ny) | raster([win.difference(box(75.8, 75.8, 124.2, 124.2))], x0, y0, nx, ny)
    if os.environ.get("NOVIA"):
        viablk[:] = True
    def cell(p):
        return int(round((p[0] - x0) / RES)), int(round((p[1] - y0) / RES))
    sa, sc = cell(a), cell(c)
    L = len(SIG)
    starts = [(li, sa[0], sa[1]) for li, l in enumerate(SIG) if l in alayers]
    goals = {(li, sc[0], sc[1]) for li, l in enumerate(SIG) if l in clayers}
    # endpoints sit on their own pad: clear a small disc there
    for li in range(L):
        for (cx, cy) in (sa, sc):
            r = int((w / 2 + 0.05) / RES) + 1
            blocked[li][max(cy - r, 0):cy + r + 1, max(cx - r, 0):cx + r + 1] = False
    VIA_COST = 1.0 / RES * 1.2
    dirs = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    def hcost(li, x, y):
        return math.hypot(x - sc[0], y - sc[1])
    dist = {}; prev = {}; pq = []
    for s in starts:
        dist[s] = 0; heapq.heappush(pq, (hcost(*s), 0, s))
    found = None
    while pq:
        f, g, s = heapq.heappop(pq)
        if g > dist.get(s, 1e18):
            continue
        if s in goals:
            found = s; break
        li, x, y = s
        for dx, dy, cst in dirs:
            nx_, ny_ = x + dx, y + dy
            if not (0 <= nx_ < nx and 0 <= ny_ < ny) or blocked[li][ny_, nx_]:
                continue
            n = (li, nx_, ny_); ng = g + cst
            if ng < dist.get(n, 1e18):
                dist[n] = ng; prev[n] = s; heapq.heappush(pq, (ng + hcost(*n), ng, n))
        if not viablk[y, x]:
            for lj in range(L):
                if lj != li and not blocked[lj][y, x]:
                    n = (lj, x, y); ng = g + VIA_COST
                    if ng < dist.get(n, 1e18):
                        dist[n] = ng; prev[n] = s; heapq.heappush(pq, (ng + hcost(*n), ng, n))
    if not found:
        return None
    path = [found]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    # string-pull each single-layer run: keep a point only where line of sight breaks
    def clear_line(li, p, q):
        n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1]))) + 1
        for k in range(n + 1):
            x = round(p[0] + (q[0] - p[0]) * k / n); y = round(p[1] + (q[1] - p[1]) * k / n)
            if blocked[li][y, x]:
                return False
        return True
    out = []
    i = 0
    while i < len(path):
        j = i
        while j + 1 < len(path) and path[j + 1][0] == path[i][0]:
            j += 1
        run = path[i:j + 1]
        k = 0; keep = [run[0]]
        while k < len(run) - 1:
            m = len(run) - 1
            while m > k + 1 and not clear_line(run[k][0], run[k][1:], run[m][1:]):
                m -= 1
            keep.append(run[m]); k = m
        out += keep
        i = j + 1
    pts = [(SIG[li], x0 + x * RES, y0 + y * RES) for li, x, y in out]
    return pts

def emit(netcode, pts, w):
    ni = b.FindNet(netcode)
    segs, vias = [], []
    run = [pts[0]]
    for p in pts[1:]:
        if p[0] != run[-1][0]:
            vias.append((p[1], p[2])); segs.append(run); run = [p]
        else:
            run.append(p)
    segs.append(run)
    for run in segs:
        if len(run) < 2:
            continue
        # keep corner points only
        keep = [run[0]]
        for i in range(1, len(run) - 1):
            d1 = (run[i][1] - run[i - 1][1], run[i][2] - run[i - 1][2])
            d2 = (run[i + 1][1] - run[i][1], run[i + 1][2] - run[i][2])
            if abs(d1[0] * d2[1] - d1[1] * d2[0]) > 1e-9:
                keep.append(run[i])
        keep.append(run[-1])
        for p, q in zip(keep, keep[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(mm(p[1]), mm(p[2]))); t.SetEnd(pcbnew.VECTOR2I(mm(q[1]), mm(q[2])))
            t.SetWidth(mm(w)); t.SetLayer(p[0]); t.SetNet(ni); b.Add(t)
            ITEMS.append((netcode, p[0], LineString([(p[1], p[2]), (q[1], q[2])]).buffer(w / 2), t))
    for x, y in vias:
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DR)); v.SetNet(ni)
        b.Add(v)
        for l in SIG:
            ITEMS.append((netcode, l, Point(x, y).buffer(VIA_D / 2), v))
        HOLES.append(Point(x, y).buffer(VIA_DR / 2))
    return len(vias)

def endpoint(desc, pos, netname, other):
    """resolve a DRC item to (x, y, layers) on the net"""
    layer = None
    for nm, l in BYNAME.items():
        if f" on {nm}" in desc:
            layer = l
    best = None
    for n, l, g, obj in ITEMS:
        if obj is None or b.FindNet(n).GetNetname() != netname:
            continue
        if layer is not None and l != layer:
            continue
        d = g.distance(Point(pos))
        if best is None or d < best[0]:
            best = (d, obj, l)
    _, obj, l = best
    if isinstance(obj, pcbnew.PAD):
        p = obj.GetPosition()
        return (tomm(p.x), tomm(p.y)), [ll for ll in SIG if obj.IsOnLayer(ll)]
    if obj.GetClass() == "PCB_VIA":
        p = obj.GetPosition()
        return (tomm(p.x), tomm(p.y)), SIG
    s, e = obj.GetStart(), obj.GetEnd()
    s, e = (tomm(s.x), tomm(s.y)), (tomm(e.x), tomm(e.y))
    pick = s if math.dist(s, other) < math.dist(e, other) else e
    return pick, [obj.GetLayer()]

def main():
    global ITEMS
    d = json.load(open(sys.argv[1]))
    nets_only = set(sys.argv[2:])
    done = fail = 0
    for u in d["unconnected_items"]:
        it = u["items"]
        if any(i["description"].startswith("Zone") for i in it):
            continue
        net = it[0]["description"].split("[")[1].split("]")[0]
        if nets_only and net not in nets_only:
            continue
        pa = (it[0]["pos"]["x"], it[0]["pos"]["y"]); pc = (it[1]["pos"]["x"], it[1]["pos"]["y"])
        a, al = endpoint(it[0]["description"], pa, net, pc)
        c, cl = endpoint(it[1]["description"], pc, net, a)
        nc = b.FindNet(net).GetNetCode()
        pts = None
        for w in widths_for(net):
            pts = route(nc, a, al, c, cl, w)
            if pts is not None:
                break
        if pts is None and os.environ.get("RIP_GND") and net != "GND":
            # rip the GND stitching stubs (0.25 mm tracks and their vias) near this connection,
            # route the signal, and let the stitching pass put GND back around it
            gnd = b.FindNet("GND").GetNetCode()
            win = box(min(a[0], c[0]) - 1.5, min(a[1], c[1]) - 1.5, max(a[0], c[0]) + 1.5, max(a[1], c[1]) + 1.5)
            rip = {}
            for n, l, g, obj in ITEMS:
                if n == gnd and obj is not None and not isinstance(obj, pcbnew.PAD) and g.intersects(win):
                    if obj.GetClass() == "PCB_VIA" or abs(tomm(obj.GetWidth()) - 0.25) < 1e-3:
                        rip[str(obj.m_Uuid.AsString())] = obj
            ITEMS[:] = [it_ for it_ in ITEMS if it_[3] is None or isinstance(it_[3], pcbnew.PAD) or str(it_[3].m_Uuid.AsString()) not in rip]
            for obj in rip.values():
                if obj.GetClass() == "PCB_VIA":
                    pp = Point(tomm(obj.GetPosition().x), tomm(obj.GetPosition().y))
                    HOLES[:] = [h for h in HOLES if h.distance(pp) > 0.01]
                b.Delete(obj)
            print("ripped", len(rip), "GND stitch items near", net)
            for w2 in widths_for(net):
                w = w2; pts = route(nc, a, al, c, cl, w)
                if pts is not None:
                    break
        if pts is None:
            print("FAIL", net, a, c); fail += 1; continue
        nv = emit(nc, pts, w); done += 1
        print("routed", net, "w", w, "vias", nv)
    pcbnew.SaveBoard(PCB, b)
    print("done", done, "failed", fail)


if __name__ == "__main__":
    main()