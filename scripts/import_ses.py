"""Import a Specctra SES (Freerouting output) into the board by adding tracks/vias directly,
then add GND pours on the outer and inner signal layers, fill zones and save.
(pcbnew.ImportSpecctraSES leaves the board in a state that crashes SaveBoard in headless KiCad 9.)
Usage (in chroot): python3 import_ses.py [ses]"""
import os, re, sys, pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import parse

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "fc.kicad_pcb")
SES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "fc.ses")
b = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM
LAYERS = {"F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu, "In3.Cu": pcbnew.In3_Cu,
          "In4.Cu": pcbnew.In4_Cu, "B.Cu": pcbnew.B_Cu}

if not os.environ.get("KEEP"):
    for t in list(b.GetTracks()):
        b.Delete(t)

tree = parse(open(SES).read())[0]

def find(node, key):
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            yield x

routes = next(find(tree, "routes"))
res = next(find(routes, "resolution"))
scale = {"um": 1e-3, "mil": 0.0254, "mm": 1.0}[res[1]] / float(res[2])   # SES unit -> mm
net_out = next(find(routes, "network_out"))

def pt(x, y):
    return pcbnew.VECTOR2I(mm(float(x) * scale), mm(-float(y) * scale))

nt = nv = 0
for net in find(net_out, "net"):
    name = net[1]
    ni = b.FindNet(name)
    if ni is None:
        print("unknown net", name); continue
    for w in find(net, "wire"):
        path = next(find(w, "path"))
        layer, width, coords = path[1], float(path[2]) * scale, path[3:]
        coords = [c for c in coords if not isinstance(c, list)]
        pts = [pt(coords[i], coords[i + 1]) for i in range(0, len(coords) - 1, 2)]
        for a, c in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(a); t.SetEnd(c); t.SetWidth(mm(width))
            t.SetLayer(LAYERS[layer]); t.SetNet(ni)
            b.Add(t); nt += 1
    for v in find(net, "via"):
        m = re.search(r"_(\d+):(\d+)_um", v[1])
        dia, drill = int(m.group(1)) / 1000, int(m.group(2)) / 1000
        via = pcbnew.PCB_VIA(b)
        via.SetPosition(pt(v[2], v[3]))
        via.SetViaType(pcbnew.VIATYPE_THROUGH)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        via.SetWidth(mm(dia)); via.SetDrill(mm(drill))
        via.SetNet(ni)
        b.Add(via); nv += 1
print("tracks", nt, "vias", nv)

def has_zone(layer):
    return any(z.GetLayer() == layer and z.GetNetname() == "GND" for z in b.Zones())

for layer in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu):
    if has_zone(layer):
        continue
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNet(b.FindNet("GND"))
    ol = pcbnew.SHAPE_POLY_SET(); ol.NewOutline()
    for x, y in [(75.3, 75.3), (124.7, 75.3), (124.7, 124.7), (75.3, 124.7)]:
        ol.Append(mm(x), mm(y))
    ol.thisown = 0   # zone takes ownership of the outline
    z.SetOutline(ol)
    z.SetLocalClearance(mm(0.2))
    z.SetMinThickness(mm(0.2))
    z.SetAssignedPriority(0)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)   # SMD pads solid, THT relieved
    z.SetThermalReliefGap(mm(0.2)); z.SetThermalReliefSpokeWidth(mm(0.25))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    b.Add(z)
pcbnew.SaveBoard(PCB, b)
print("saved (unfilled)")
b.BuildConnectivity()
filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print("saved (filled)")
