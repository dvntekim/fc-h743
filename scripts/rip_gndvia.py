"""Delete GND vias named in DRC errors against other items (vias left under parts that moved)."""
import os, json, pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
d = json.load(open(os.path.join(HERE, "drc_last.json")))
ids = set()
for v in d["violations"]:
    if v["severity"] == "error":
        for i in v["items"]:
            if i["description"].startswith("Via [GND]"):
                ids.add(i["uuid"])
n = 0
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString() in ids:
        b.Delete(t); n += 1
pcbnew.SaveBoard(PCB, b); print("ripped", n)
