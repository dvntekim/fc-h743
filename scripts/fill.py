"""Refill all zones and save. GND pours on signal layers join SMD pads solid (THT relieved)."""
import os, pcbnew
PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
for z in b.Zones():
    if not z.GetIsRuleArea() and z.GetNetname() == "GND" and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu):
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
b.BuildConnectivity()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print("filled")
