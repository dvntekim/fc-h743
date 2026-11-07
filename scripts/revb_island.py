"""Rev B: cut the IMU island (two milled slots + copper-free edge bridges) and place the island parts.
Geometry from sim/thermal/island_corner_final.json (corner bridge 2.2 mm of copper, 1.1 W heater)."""
import os, math, pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
F = pcbnew.FromMM; V = lambda x, y: pcbnew.VECTOR2I(F(x), F(y))

# slots as oblongs: (end centre 1, end centre 2), width 1.0 mm
SLOTS = [((118.5, 76.5), (118.5, 86.7)), ((121.1, 89.5), (123.5, 89.5))]
KEEPOUT = [(117.8, 74.8, 119.2, 76.6, "island edge bridge (top)"), (123.6, 88.8, 125.2, 90.2, "island edge bridge (right)")]
R = 0.5

def seg_dist(p, a, c):
    ax, ay = a; cx, cy = c; dx, dy = cx-ax, cy-ay; L = dx*dx+dy*dy
    u = max(0, min(1, ((p[0]-ax)*dx+(p[1]-ay)*dy)/L)); return math.dist(p, (ax+u*dx, ay+u*dy))

def in_keep(p, m=0):
    return any(x0-m <= p[0] <= x1+m and y0-m <= p[1] <= y1+m for x0, y0, x1, y1, _ in KEEPOUT)

# 1. vias and tracks in the slots / bridges
n = 0
for t in list(b.GetTracks()):
    pts = [t.GetPosition()] if t.GetClass() == "PCB_VIA" else [t.GetStart(), t.GetEnd()]
    pts = [(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)) for p in pts]
    if any(seg_dist(p, a, c) < R + 0.75 or in_keep(p, 0.4) for p in pts for a, c in SLOTS):
        b.Delete(t); n += 1
print("removed tracks/vias", n)

# 2. Edge.Cuts slots
def line(a, c):
    s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(F(0.05))
    s.SetStart(V(*a)); s.SetEnd(V(*c)); b.Add(s)
def arc(st, mid, en):
    s = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_ARC); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(F(0.05))
    s.SetArcGeometry(V(*st), V(*mid), V(*en)); b.Add(s)
for (x1, y1), (x2, y2) in SLOTS:
    ux, uy = (x2-x1), (y2-y1); L = math.hypot(ux, uy); ux, uy = ux/L, uy/L; nx, ny = -uy, ux
    a1 = (x1+nx*R, y1+ny*R); a2 = (x2+nx*R, y2+ny*R); b1 = (x1-nx*R, y1-ny*R); b2 = (x2-nx*R, y2-ny*R)
    line(a1, a2); line(b1, b2)
    arc(a2, (x2+ux*R, y2+uy*R), b2); arc(b1, (x1-ux*R, y1-uy*R), a1)

# 3. copper-free edge bridges: keepouts on every copper layer
for x0, y0, x1, y1, name in KEEPOUT:
    z = pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetZoneName(name)
    ls = pcbnew.LSET(); [ls.AddLayer(l) for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu)]
    z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowPads(True)
    z.SetDoNotAllowCopperPour(True); z.SetDoNotAllowFootprints(False)
    o = z.Outline(); o.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        o.Append(F(x), F(y))
    b.Add(z)

# 4. place the island parts (F: heater + cut-off; B: IMUs, decoupling, CS pull-ups)
PLACE = {
    "R44": ("F", 120.70, 78.90, 90), "R45": ("F", 120.70, 85.40, 270),
    "U23": ("F", 123.35, 83.30, 90), "C62": ("F", 123.35, 85.60, 90),
    "U21": ("B", 121.55, 79.55, 90), "U20": ("B", 121.55, 84.55, 0),
    "C48": ("B", 124.00, 77.30, 90), "C47": ("B", 124.00, 79.30, 90), "R36": ("B", 124.00, 81.30, 90),
    "R37": ("B", 124.00, 83.30, 90), "C44": ("B", 124.00, 85.30, 90), "C45": ("B", 124.00, 87.30, 90),
    "C46": ("B", 120.30, 87.55, 0), "R35": ("B", 122.40, 87.55, 0),
}
for ref, (side, x, y, rot) in PLACE.items():
    f = b.FindFootprintByReference(ref)
    if (side == "B") != f.IsFlipped():
        f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    f.SetPosition(V(x, y)); f.SetOrientationDegrees(rot)
    print(ref, side, x, y, rot)
# fiducial off the island
fid = b.FindFootprintByReference("FID2"); fid.SetPosition(V(112.0, 77.6))
pcbnew.SaveBoard(PCB, b)
print("saved")
