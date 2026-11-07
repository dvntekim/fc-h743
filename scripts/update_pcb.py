"""Apply schematic changes to the hand-finished board (KiCad's 'Update PCB from schematic', scripted).

Reads fc.net (kicad-cli netlist of the regenerated schematic) and, on kicad/fc.kicad_pcb:
  * adds footprints that are new (placed at NEW_AT, to be moved after),
  * swaps footprints whose library footprint changed, keeping position, side and rotation,
  * updates value, LCSC field and symbol path,
  * deletes footprints whose reference no longer exists,
  * re-assigns every pad net from the netlist.
Usage (chroot): python3 update_pcb.py
"""
import os, sys
import pcbnew
from sexp import parse, find, find1

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "kicad", "fc.kicad_pcb")
KFP = "/usr/share/kicad/footprints"
NEW_AT = (121.5, 82.0)


def load_netlist(path):
    root = parse(open(path).read())[0]
    comps = {}
    for c in find(find1(root, "components"), "comp"):
        ref = find1(c, "ref")[1]
        fields = {}
        fl = find1(c, "fields")
        if fl:
            for f in find(fl, "field"):
                fields[find1(f, "name")[1]] = f[2] if len(f) > 2 and isinstance(f[2], str) else ""
        sp = find1(c, "sheetpath")
        comps[ref] = dict(ref=ref, value=find1(c, "value")[1], fp=find1(c, "footprint")[1] if find1(c, "footprint") else "",
                          fields=fields, path=find1(sp, "tstamps")[1] + find1(c, "tstamps")[1])
    pinnet = {}
    for n in find(find1(root, "nets"), "net"):
        name = find1(n, "name")[1]
        for node in find(n, "node"):
            pinnet[(find1(node, "ref")[1], find1(node, "pin")[1])] = name
    return comps, pinnet


def load_fp(fpid):
    lib, name = fpid.split(":")
    libdir = os.path.join(HERE, "kicad", "fc_custom.pretty") if lib == "fc_custom" else f"{KFP}/{lib}.pretty"
    fp = pcbnew.FootprintLoad(libdir, name)
    if fp is None:
        raise SystemExit(f"cannot load {fpid}")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def set_lcsc(fp, val):
    if fp.HasFieldByName("LCSC"):
        fp.GetFieldByName("LCSC").SetText(val)
    elif val:
        f = pcbnew.PCB_FIELD(fp, fp.GetNextFieldId(), "LCSC")
        f.SetText(val); f.SetVisible(False); f.SetLayer(pcbnew.F_Fab)
        fp.AddField(f)


b = pcbnew.LoadBoard(PCB)
comps, pinnet = load_netlist(os.path.join(HERE, "fc.net"))
nets = {n.GetNetname(): n for n in b.GetNetsByName().values()}


def net(name):
    if name not in nets:
        ni = pcbnew.NETINFO_ITEM(b, name); b.Add(ni); nets[name] = ni
    return nets[name]


onboard = {f.GetReference(): f for f in b.GetFootprints()}
for ref, f in onboard.items():
    if ref not in comps:
        b.Remove(f); print("removed", ref)
for ref, c in sorted(comps.items()):
    if not c["fp"]:
        continue
    f = onboard.get(ref)
    want = c["fp"]
    if f is None or f.GetFPIDAsString() != want:
        nf = load_fp(want)
        nf.SetReference(ref)
        if f is not None:
            pos, rot, flipped = f.GetPosition(), f.GetOrientationDegrees(), f.IsFlipped()
            b.Remove(f)
            print("swapped", ref, "->", want)
        else:
            pos, rot, flipped = pcbnew.VECTOR2I(pcbnew.FromMM(NEW_AT[0]), pcbnew.FromMM(NEW_AT[1])), 0.0, False
            print("added", ref, want)
        b.Add(nf)
        nf.SetPosition(pos)
        if flipped:
            nf.Flip(pos, pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        nf.SetOrientationDegrees(rot)
        f = nf
    if f.GetValue() != c["value"]:
        print("value", ref, f.GetValue(), "->", c["value"])
        f.SetValue(c["value"])
    set_lcsc(f, c["fields"].get("LCSC", ""))
    f.SetPath(pcbnew.KIID_PATH(c["path"]))
    for pad in f.Pads():
        n = pinnet.get((ref, pad.GetNumber()))
        if n and pad.GetNetname() != n:
            pad.SetNet(net(n))
pcbnew.SaveBoard(PCB, b)
print("saved")
