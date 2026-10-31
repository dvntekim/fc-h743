"""VIN copper pour on F.Cu above the TPS54360B: ties pin 2 to the VBAT vias with a wide path."""
import os, pcbnew
PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB); mm = pcbnew.FromMM
for z in [z for z in b.Zones() if z.GetZoneName() == "VIN"]:
    b.Remove(z)
z = pcbnew.ZONE(b); z.SetLayer(pcbnew.F_Cu); z.SetNet(b.FindNet("VBAT")); z.SetZoneName("VIN")
ol = pcbnew.SHAPE_POLY_SET(); ol.NewOutline()
for x, y in [(83.2, 102.1), (87.25, 102.1), (87.25, 104.65), (83.2, 104.65)]:
    ol.Append(mm(x), mm(y))
ol.thisown = 0; z.SetOutline(ol)
z.SetAssignedPriority(9); z.SetLocalClearance(mm(0.2)); z.SetMinThickness(mm(0.25))
z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
b.Add(z)
# EN escapes pin 3 straight into a via, so the pour stays one piece around it
en = b.FindNet("BUCK_EN")
p3 = next(p for p in b.FindFootprintByReference("U1").Pads() if p.GetNumber() == "3").GetPosition()
x = p3.x; y = mm(103.45)
t = pcbnew.PCB_TRACK(b); t.SetStart(p3); t.SetEnd(pcbnew.VECTOR2I(x, y)); t.SetWidth(mm(0.2)); t.SetLayer(pcbnew.F_Cu); t.SetNet(en); b.Add(t)
v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(x, y)); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
v.SetWidth(mm(0.45)); v.SetDrill(mm(0.2)); v.SetNet(en); b.Add(v)
pcbnew.SaveBoard(PCB, b); print("VIN pour added, EN via placed")
