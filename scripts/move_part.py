"""Move one footprint to the nearest spot (spiral search) where its pads and courtyard clear
every other net's copper and every other courtyard on its side. Tracks on its nets that touch
its pads must already be removed. Usage: python3 move_part.py REF [x y]"""
import sys, os, math
ref = sys.argv[1]
tx = float(sys.argv[2]) if len(sys.argv) > 2 else None
ty = float(sys.argv[3]) if len(sys.argv) > 3 else None
sys.argv = [sys.argv[0], os.path.join(os.path.dirname(os.path.abspath(__file__)), "drc_last.json")]
import fix_route as fr, pcbnew
from shapely.geometry import Point, box
b = fr.b
fp = b.FindFootprintByReference(ref)
if os.environ.get("SIDE") == "top" and fp.IsFlipped():
    fp.SetLayerAndFlip(pcbnew.F_Cu)
elif os.environ.get("SIDE") == "bot" and not fp.IsFlipped():
    fp.SetLayerAndFlip(pcbnew.B_Cu)
layer = pcbnew.B_Cu if fp.IsFlipped() else pcbnew.F_Cu
crt = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
x0, y0 = fr.tomm(fp.GetPosition().x), fr.tomm(fp.GetPosition().y)
tx = x0 if tx is None else tx; ty = y0 if ty is None else ty
mine = {id(p) for p in fp.Pads()}
others = [(n, g) for n, l, g, o in fr.ITEMS if l == layer and not (isinstance(o, pcbnew.PAD) and o.GetParentFootprint().GetReference() == ref)]
holes = fr.HOLES
def court(f):
    f.BuildCourtyardCaches(); c = f.GetCourtyard(crt)
    return fr.poly_of(c)
courts = [court(f) for f in b.GetFootprints() if f.GetReference() != ref and f.IsFlipped() == fp.IsFlipped() and court(f).area > 0]
AV = [float(v) for v in os.environ["AVOID"].split(",")] if os.environ.get("AVOID") else None
def ok():
    if AV and court(fp).intersects(box(*AV)):
        return False
    if not court(fp).is_valid or any(court(fp).intersects(c) for c in courts):
        return False
    for p in fp.Pads():
        g = fr.poly_of(p.GetEffectivePolygon(layer, pcbnew.ERROR_INSIDE))
        for n, o in others:
            if n != p.GetNetCode() and o.distance(g) < 0.12:
                return False
        if any(h.distance(g) < 0.2 for h in holes):
            return False
    return True
for rad in [i * 0.1 for i in range(0, 40)]:
    k = max(1, int(2 * math.pi * rad / 0.1))
    found = False
    for j in range(k):
        a = 2 * math.pi * j / k
        for rot in (fp.GetOrientationDegrees(), fp.GetOrientationDegrees() + 90):
            fp.SetPosition(pcbnew.VECTOR2I(fr.mm(tx + rad * math.cos(a)), fr.mm(ty + rad * math.sin(a))))
            fp.SetOrientationDegrees(rot)
            if ok():
                found = True; break
        if found: break
    if found: break
print(ref, "moved to", round(fr.tomm(fp.GetPosition().x), 2), round(fr.tomm(fp.GetPosition().y), 2), fp.GetOrientationDegrees(), "found" if found else "NOT FOUND")
if found:
    pcbnew.SaveBoard(fr.PCB, b)
