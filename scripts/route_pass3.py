"""Clear GND tracks around connections still open (from drc_last.json) so Freerouting can route
the signal first and then GND, then export fc3.dsn (no pours on signal layers)."""
import os, sys, json, pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "fc.kicad_pcb")
b = pcbnew.LoadBoard(PCB)
d = json.load(open(os.path.join(HERE, "drc_last.json")))
R = float(os.environ.get("RIP_R", "1.5"))
wins = []
for u in d["unconnected_items"]:
    it = u["items"]
    if any(i["description"].startswith("Zone") for i in it):
        continue
    xs = [i["pos"]["x"] for i in it]; ys = [i["pos"]["y"] for i in it]
    if os.environ.get("CORRIDOR"):
        from shapely.geometry import LineString
        wins.append(LineString(list(zip(xs, ys))).buffer(R))
    else:
        wins.append((min(xs) - R, min(ys) - R, max(xs) + R, max(ys) + R))
gnd = b.FindNet("GND").GetNetCode()
n = 0
for t in list(b.GetTracks()):
    if t.GetNetCode() != gnd and not os.environ.get("RIP_ALL"):
        continue
    p = t.GetPosition() if t.GetClass() == "PCB_VIA" else t.GetStart()
    q = t.GetPosition() if t.GetClass() == "PCB_VIA" else t.GetEnd()
    from shapely.geometry import Point as _P, LineString as _L
    seg = _L([(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)), (pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)+1e-6)])
    for w_ in wins:
        if isinstance(w_, tuple):
            x0, y0, x1, y1 = w_
            hit = any(x0 <= pcbnew.ToMM(v.x) <= x1 and y0 <= pcbnew.ToMM(v.y) <= y1 for v in (p, q))
        else:
            hit = w_.intersects(seg)
        if hit:
            b.Delete(t); n += 1; break
for z in list(b.Zones()):
    if not z.GetIsRuleArea() and z.GetNetname() == "GND" and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu):
        b.Remove(z)
print("ripped", n, "in", len(wins), "windows")
pcbnew.SaveBoard(PCB, b)
print("dsn", pcbnew.ExportSpecctraDSN(b, os.path.join(HERE, "fc3.dsn")))
