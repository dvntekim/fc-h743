"""Set design rules, layer roles and plane zones, then export a Specctra DSN for Freerouting.
Stackup JLC06161H-3313: F.Cu sig | In1 GND | In2 sig | In3 sig+pours | In4 GND | B.Cu sig.
Every signal layer sits next to a solid GND plane; +3V3 is routed and poured."""
import os, pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
ds = b.GetDesignSettings()
ds.m_MinClearance = mm(0.1); ds.m_TrackMinWidth = mm(0.1); ds.m_ViasMinSize = mm(0.35)
ds.m_MinThroughDrill = mm(0.15); ds.m_CopperEdgeClearance = mm(0.3); ds.m_HoleClearance = mm(0.2)
ds.m_HoleToHoleMin = mm(0.25); ds.m_MinResolvedSpokes = 1; ds.m_ViasMinAnnularWidth = mm(0.1)
for l in (pcbnew.In1_Cu, pcbnew.In4_Cu):
    b.SetLayerType(l, pcbnew.LT_POWER)
for l in (pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.B_Cu):
    b.SetLayerType(l, pcbnew.LT_SIGNAL)
# remove old zones
for z in list(b.Zones()):
    b.Remove(z)

def zone(layer, netname, prio=0, clr=0.2, thermal=True):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNet(b.FindNet(netname))
    ol = pcbnew.SHAPE_POLY_SET(); ol.NewOutline()
    for x, y in [(75.3, 75.3), (124.7, 75.3), (124.7, 124.7), (75.3, 124.7)]:
        ol.Append(mm(x), mm(y))
    ol.thisown = 0   # zone takes ownership of the outline
    z.SetOutline(ol)
    z.SetLocalClearance(mm(clr))
    z.SetMinThickness(mm(0.2))
    z.SetAssignedPriority(prio)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL if thermal else pcbnew.ZONE_CONNECTION_FULL)
    z.SetThermalReliefGap(mm(0.2)); z.SetThermalReliefSpokeWidth(mm(0.25))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    b.Add(z)
    return z

zone(pcbnew.In1_Cu, "GND"); zone(pcbnew.In4_Cu, "GND")

# 0.5 mm ring along the board edge: no tracks or vias (pads and pours allowed)
def keepout(x0, y0, x1, y1):
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowCopperPour(False) if hasattr(z, "SetDoNotAllowCopperPour") else z.SetDoNotAllowZoneFills(False); z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET(); [ls.AddLayer(l) for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu)]
    z.SetLayerSet(ls)
    ol = pcbnew.SHAPE_POLY_SET(); ol.NewOutline()
    for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
        ol.Append(mm(x), mm(y))
    ol.thisown = 0
    z.SetOutline(ol)
    z.SetZoneName("edge keepout")
    b.Add(z)
E = 0.55
keepout(74.9, 74.9, 125.1, 75 + E); keepout(74.9, 125 - E, 125.1, 125.1)
keepout(74.9, 74.9, 75 + E, 125.1); keepout(125 - E, 74.9, 125.1, 125.1)
pcbnew.SaveBoard(PCB, b)
ok = pcbnew.ExportSpecctraDSN(b, os.path.join(HERE, "fc.dsn"))
print("dsn", ok)
