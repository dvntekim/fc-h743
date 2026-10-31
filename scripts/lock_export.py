"""Lock every existing track/via (exported as fixed wiring), drop signal-layer pours and export
fc7.dsn, so Freerouting only adds the missing connections and cannot rip anything."""
import os, pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
for t in b.GetTracks():
    t.SetLocked(True)
for z in list(b.Zones()):
    if not z.GetIsRuleArea() and z.GetNetname() == "GND" and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu):
        b.Remove(z)
print("dsn", pcbnew.ExportSpecctraDSN(b, os.path.join(HERE, "fc7.dsn")))
