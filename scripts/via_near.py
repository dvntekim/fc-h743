"""Find the nearest spot to a GND pad where a via fits on every layer, place it, and route the pad
to it with the local router. Usage: via_near.py REF:PAD [radius]"""
import sys, os, math
ref, pad = sys.argv[1].split(":"); R = float(sys.argv[2]) if len(sys.argv) > 2 else 2.5
sys.argv = [sys.argv[0], os.path.join(os.path.dirname(os.path.abspath(__file__)), "drc_last.json")]
import fix_route as fr, pcbnew
from shapely.geometry import Point
b = fr.b; G = b.FindNet("GND").GetNetCode()
p = next(q for q in b.FindFootprintByReference(ref).Pads() if q.GetNumber() == pad)
s = (fr.tomm(p.GetPosition().x), fr.tomm(p.GetPosition().y)); sl = [l for l in fr.SIG if p.IsOnLayer(l)]
def via_ok(x, y):
    c = Point(x, y)
    for n, l, g, _ in fr.ITEMS:
        if n != G and g.distance(c) < fr.VIA_D / 2 + max(0.12, fr.net_clr(n) + 0.01):
            return False
    for h in fr.HOLES:
        if h.distance(c) < fr.VIA_DR / 2 + 0.3:
            return False
    for poly, ls, nt, nv in fr.KEEP:
        if nv and poly.distance(c) < fr.VIA_D / 2 + 0.05:
            return False
    # no other-net pads on any layer (F pads above a bottom pad, etc.)
    return True
cands = []
k = 0.05
for i in range(int(-R / k), int(R / k) + 1):
    for j in range(int(-R / k), int(R / k) + 1):
        x, y = s[0] + i * k, s[1] + j * k
        d = math.hypot(i * k, j * k)
        if 0.45 <= d <= R:
            cands.append((d, x, y))
cands.sort()
for d, x, y in cands:
    if not via_ok(x, y):
        continue
    for w in (0.2, 0.15, 0.127):
        pts = fr.route(G, s, sl, (x, y), [l for l in fr.SIG], w)
        if pts:
            v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(fr.mm(x), fr.mm(y))); v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetWidth(fr.mm(fr.VIA_D)); v.SetDrill(fr.mm(fr.VIA_DR)); v.SetNet(b.FindNet(G)); b.Add(v)
            fr.emit(G, pts, w)
            pcbnew.SaveBoard(fr.PCB, b); print("via at", round(x, 2), round(y, 2), "dist", round(d, 2), "w", w); sys.exit(0)
        break
print("FAILED")
