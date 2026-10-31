"""Prepare a completion pass: drop the GND pours on signal layers (Freerouting would read them
as planes), keep every track and via, export fc2.dsn. Freerouting then routes only what is open."""
import os, pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
for z in list(b.Zones()):
    if not z.GetIsRuleArea() and z.GetNetname() == "GND" and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu):
        b.Remove(z)
b.GetDesignSettings().m_MinResolvedSpokes = 1
print("dsn", pcbnew.ExportSpecctraDSN(b, os.path.join(HERE, "fc2.dsn")))
