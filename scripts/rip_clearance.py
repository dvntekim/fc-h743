"""Delete the non-GND tracks named in DRC clearance errors (drc_last.json) so they can be re-routed."""
import os, json, pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
d = json.load(open(os.path.join(HERE, "drc_last.json")))
ids = set()
for v in d["violations"]:
    if v["type"] in ("clearance", "hole_clearance", "copper_edge_clearance", "items_not_allowed", "track_dangling", "via_dangling", "shorting_items"):
        for i in v["items"]:
            if (i["description"].startswith("Track") and "[GND]" not in i["description"]) or (v["type"].endswith("dangling")):
                ids.add(i["uuid"])
n = 0
for t in list(b.GetTracks()):
    if t.m_Uuid.AsString() in ids:
        b.Delete(t); n += 1
pcbnew.SaveBoard(PCB, b)
print("ripped", n)
