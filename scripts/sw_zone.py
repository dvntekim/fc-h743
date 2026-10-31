"""Rebuild the switch-node pour as the convex hull of the BUCK_SW pads (U1.8, D3.1, L1.1, C9.2)."""
import os, pcbnew
from shapely.geometry import MultiPoint
PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB); mm, to = pcbnew.FromMM, pcbnew.ToMM
pts = []
for r, n in (("U1", "8"), ("D3", "1"), ("L1", "1"), ("C9", "2")):
    p = next(p for p in b.FindFootprintByReference(r).Pads() if p.GetNumber() == n)
    ol = p.GetEffectivePolygon(pcbnew.F_Cu, pcbnew.ERROR_INSIDE).Outline(0)
    pts += [(to(ol.CPoint(j).x), to(ol.CPoint(j).y)) for j in range(ol.PointCount())]
hull = MultiPoint(pts).convex_hull
z = next(z for z in b.Zones() if z.GetNetname() == "BUCK_SW")
ol = pcbnew.SHAPE_POLY_SET(); ol.NewOutline()
for x, y in list(hull.exterior.coords)[:-1]:
    ol.Append(mm(x), mm(y))
ol.thisown = 0; z.SetOutline(ol)
pcbnew.SaveBoard(PCB, b); print("SW pour", round(hull.area, 1), "mm2")
# keep other nets' tracks and vias out of the switch-node area on F.Cu so the pour stays whole
for k in [k for k in b.Zones() if k.GetIsRuleArea() and k.GetZoneName() == "SW keepout"]:
    b.Remove(k)
k = pcbnew.ZONE(b); k.SetIsRuleArea(True); k.SetZoneName("SW keepout"); k.SetLayer(pcbnew.F_Cu)
k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True); k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
if hasattr(k, "SetDoNotAllowCopperPour"):
    k.SetDoNotAllowCopperPour(False)
ol2 = pcbnew.SHAPE_POLY_SET(); ol2.NewOutline()
for x, y in list(hull.buffer(-0.05).exterior.coords)[:-1]:
    ol2.Append(mm(x), mm(y))
ol2.thisown = 0; k.SetOutline(ol2); b.Add(k)
pcbnew.SaveBoard(PCB, b); print("SW keepout added")
