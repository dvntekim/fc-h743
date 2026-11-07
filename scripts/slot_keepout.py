"""Routing keepouts 0.3 mm around the island slots (the fab's copper-to-edge clearance), so the
autorouter, which does not know the edge-clearance rule, keeps tracks and vias off the slot edges."""
import os, math, pcbnew
from shapely.geometry import LineString
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
SLOTS = [((118.5, 76.5), (118.5, 86.7)), ((121.1, 89.5), (123.5, 89.5))]
for z in list(b.Zones()):
    if z.GetIsRuleArea() and z.GetZoneName().startswith("slot clearance"):
        b.Remove(z)
for k, (a, c) in enumerate(SLOTS):
    g = LineString([a, c]).buffer(0.5 + 0.32, 8)
    z = pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetZoneName(f"slot clearance {k+1}")
    ls = pcbnew.LSET()
    for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu):
        ls.AddLayer(l)
    z.SetLayerSet(ls); z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowCopperPour(False); z.SetDoNotAllowFootprints(False)
    o = z.Outline(); o.NewOutline()
    for x, y in list(g.exterior.coords)[:-1]:
        o.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    b.Add(z)
pcbnew.SaveBoard(PCB, b); print("slot keepouts added")
