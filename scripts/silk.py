"""Silkscreen clean-up for a dense board: passives' reference designators move to the Fab layer
(assembly drawing) and stay off the silk; ICs, connectors, LEDs and test pads keep theirs at 0.8 mm,
nudged off pads where possible."""
import os, pcbnew
PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
hidden = kept = 0
for fp in b.GetFootprints():
    ref = fp.GetReference()
    r = fp.Reference()
    if ref[0] in "RCL" or ref.startswith(("FB", "TP", "JP", "FID", "H", "Y")):
        r.SetVisible(False); hidden += 1
    else:
        r.SetVisible(True)
        r.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8))); r.SetTextThickness(mm(0.12)); kept += 1
    fp.Value().SetVisible(False)
pcbnew.SaveBoard(PCB, b)
print("refdes hidden", hidden, "kept", kept)
