"""Build the PCB: board outline, stackup, footprints with nets from the KiCad netlist,
and placement (fixed positions for connectors/ICs, rule-based placement for passives).

Runs inside the KiCad 9 Python (pcbnew). Routing is done separately (route.py).
Coordinates: board centre at (100, 100) mm, KiCad y axis points down. "top"/"bot" = side.
"""
import math, os, sys, json
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexp import parse, find, find1

KFP = "/usr/share/kicad/footprints"
CX, CY = 100.0, 100.0
BW = BH = 50.0
X0, X1, Y0, Y1 = CX - BW / 2, CX + BW / 2, CY - BH / 2, CY + BH / 2
HOLE = 15.25            # 30.5 mm pattern
CORNER_R = 2.0

# ---------------------------------------------------------------- fixed placement
# ref: (x, y, rotation_deg, side). x/y are the footprint origin.
FIXED = {
    # MCU, top, centre. IMUs sit under it on the bottom side, inside the pin ring.
    "U10": (100.0, 100.0, 0, "top"),
    "U20": (97.6, 100.0, 0, "bot"),
    "U21": (102.4, 100.0, 0, "bot"),
    "R44": (100.0, 96.6, 0, "bot"), "R45": (100.0, 103.4, 0, "bot"),   # heater elements around
    "R46": (94.0, 100.0, 90, "bot"), "R47": (106.6, 100.0, 90, "bot"),  # the IMU pair
    # power entry, left edge, top side
    "J1": (78.3, 100.0, 90, "top"),
    "Q1": (84.4, 91.6, 0, "top"),
    "D2": (84.4, 99.2, 90, "top"),
    "U1": (84.2, 107.6, 90, "top"),
    "L1": (91.6, 113.8, 0, "top"),
    # top side edges
    "J30": (94.0, Y0 + 3.3, 180, "top"),      # CAN1, top edge
    "J38": (106.0, Y0 + 3.4, 180, "top"),     # DEBUG, top edge
    "J20": (X1 - 3.6, 96.6, 90, "top"),       # USB-C, right edge, at PA11/PA12
    "J31": (X1 - 3.3, 110.0, 90, "top"),      # CAN2, right edge
    "J36": (105.5, Y1 - 3.4, 0, "top"),       # ESC, bottom edge, under M1-M4
    "J32": (92.0, Y1 - 3.3, 0, "top"),        # TELEM1, bottom edge, under PE7-PE10
    # bottom side edges
    # microSD, bottom side, card from the left edge between H1 and H3. (The right edge is
    # taken by the USB-C shell's through-hole tabs, which would pierce the socket.)
    "J21": (X0 + 8.7, 96.0, 90, "bot"),
    "J33": (87.5, Y0 + 3.3, 180, "bot"),      # TELEM2, top edge
    "J34": (99.8, Y0 + 3.3, 180, "bot"),     # GPS/I2C, top edge
    "J35": (110.0, Y1 - 3.3, 0, "bot"),       # RC, bottom edge
    "J37": (95.0, Y1 - 3.4, 0, "bot"),        # AUX, bottom edge
    "J39": (X0 + 2.6, 110.0, 90, "bot"),      # buzzer pads, left edge
    # mounting holes and fiducials
    "H1": (CX - HOLE, CY - HOLE, 0, "top"), "H2": (CX + HOLE, CY - HOLE, 0, "top"),
    "H3": (CX - HOLE, CY + HOLE, 0, "top"), "H4": (CX + HOLE, CY + HOLE, 0, "top"),
    "FID1": (X0 + 2.5, Y0 + 2.5, 0, "top"), "FID2": (X1 - 2.5, Y0 + 2.5, 0, "top"),
    "FID3": (X0 + 2.5, Y1 - 2.5, 0, "top"),
}

# ICs and discretes placed next to the pin or connector they serve, before the passives.
IC_ANCHOR = {
    "D3": ("U1", "8", "top"),
    "Y1": ("U10", "12", "top"),
    "U40": ("J30", "2", "top"), "U7": ("J30", "1", "top"),
    "U41": ("J31", "2", "top"),
    "U30": ("J20", "A6", "top"), "F1": ("J20", "A4", "top"), "U3": ("J20", "A9", "top"),
    "U50": ("J36", "6", "top"),
    "U22": ("U10", "59", "top"),
    "U4": ("U10", "50", "top"), "L2": ("U10", "50", "top"),
    "U5": ("U10", "11", "top"),
    "U2": ("L1", "2", "top"),
    "U6": ("J33", "1", "bot"),
    "Q2": ("U10", "96", "bot"),
    "Q3": ("J39", "2", "bot"), "D20": ("J39", "2", "bot"),
    "D1": ("Q1", "4", "top"),
    "D4": ("U10", "1", "bot"),
    "D10": ("U10", "57", "bot"), "D11": ("U10", "58", "bot"), "D12": ("U10", "35", "bot"),
    "JP1": ("U10", "94", "top"),
}

# Anchors for rule-based placement: ref -> (anchor ref, anchor pad, side) ; side defaults to
# the anchor's side. Decoupling caps sit on the pin, others as close as the space allows.
ANCHOR = {
    # MCU decoupling under the pin ring (bottom side)
    "C29": ("U10", "11", "bot"), "C30": ("U10", "27", "bot"), "C31": ("U10", "50", "bot"),
    "C32": ("U10", "75", "bot"), "C33": ("U10", "100", "bot"), "C34": ("U10", "6", "bot"),
    "C35": ("U10", "50", "bot"), "C36": ("U10", "48", "bot"), "C37": ("U10", "73", "bot"),
    "FB1": ("U10", "21", "top"), "C38": ("U10", "21", "bot"), "C39": ("U10", "21", "bot"),
    "C40": ("U10", "20", "bot"), "C41": ("U10", "14", "bot"), "R27": ("U10", "94", "bot"),
    "C42": ("Y1", "1", "top"), "C43": ("Y1", "3", "top"),
    "R28": ("U10", "29", "top"), "R29": ("U10", "84", "top"), "R30": ("U10", "87", "top"),
    "R31": ("U10", "46", "top"),
    "R32": ("D10", "2", "bot"), "R33": ("D11", "2", "bot"), "R34": ("D12", "2", "bot"),
    # sensors
    "C44": ("U20", "8", "bot"), "C45": ("U20", "5", "bot"), "C46": ("U20", "5", "bot"),
    "R35": ("U20", "12", "bot"), "C47": ("U21", "3", "bot"), "C48": ("U21", "11", "bot"),
    "R36": ("U21", "14", "bot"), "R37": ("U21", "5", "bot"),
    "R38": ("U22", "5", "top"), "R39": ("U22", "7", "top"), "C49": ("U22", "10", "top"),
    "C50": ("U22", "1", "top"), "R40": ("U22", "2", "top"), "R41": ("U22", "4", "top"),
    "R42": ("Q2", "1", "bot"), "R43": ("Q2", "1", "bot"),
    # power
    "R1": ("Q1", "4", "top"), "C1": ("Q1", "1", "bot"), "C2": ("Q1", "1", "bot"),
    "C3": ("D2", "1", "bot"), "R2": ("U10", "33", "bot"), "R3": ("U10", "33", "bot"),
    "C4": ("U10", "33", "bot"), "R4": ("U10", "32", "bot"), "C5": ("U10", "32", "bot"),
    "C6": ("U1", "2", "top"), "C7": ("U1", "2", "top"), "C8": ("U1", "2", "top"),
    "C9": ("U1", "1", "top"), "R5": ("U1", "3", "top"), "R6": ("U1", "3", "top"),
    "R7": ("U1", "4", "top"), "C10": ("L1", "2", "top"), "C11": ("L1", "2", "top"),
    "C12": ("L1", "2", "bot"), "C13": ("L1", "2", "top"), "R8": ("U1", "5", "top"),
    "R9": ("U1", "5", "top"), "R10": ("U1", "6", "top"), "C14": ("U1", "6", "top"),
    "C15": ("U1", "6", "top"), "R11": ("U2", "5", "bot"), "R12": ("U3", "5", "top"),
    "C16": ("U2", "6", "bot"), "C17": ("U2", "6", "bot"), "R13": ("U10", "77", "bot"),
    "R14": ("U10", "77", "bot"), "R15": ("U10", "28", "bot"), "R16": ("U10", "28", "bot"),
    "C18": ("U10", "28", "bot"), "C19": ("U4", "4", "top"), "R17": ("U4", "5", "top"),
    "R18": ("U4", "5", "top"), "C20": ("U4", "5", "top"), "C21": ("L2", "2", "top"),
    "C22": ("L2", "2", "top"), "C23": ("U5", "1", "top"), "C24": ("U5", "5", "top"),
    "R19": ("U5", "3", "top"), "R20": ("U6", "5", "bot"), "R21": ("U6", "3", "bot"),
    "R22": ("U6", "4", "bot"), "C25": ("U6", "1", "bot"), "C26": ("U6", "6", "bot"),
    "R23": ("U7", "5", "top"), "R24": ("U7", "3", "top"), "R25": ("U7", "4", "top"),
    "C27": ("U7", "1", "top"), "C28": ("U7", "6", "top"), "R26": ("D4", "1", "bot"),
    # USB / SD
    "R48": ("J20", "A5", "top"), "R49": ("J20", "B5", "top"), "R50": ("J20", "S1", "top"),
    "C51": ("J20", "S1", "top"), "R51": ("U10", "68", "bot"), "R52": ("U10", "68", "bot"),
    "R53": ("J21", "3", "bot"), "R54": ("J21", "7", "bot"), "R55": ("J21", "8", "bot"),
    "R56": ("J21", "1", "bot"), "R57": ("J21", "2", "bot"), "C52": ("J21", "4", "bot"),
    "C53": ("J21", "4", "bot"),
    # CAN
    "C54": ("U40", "3", "top"), "C55": ("U40", "3", "top"), "C56": ("U40", "5", "top"),
    "JP41": ("U40", "7", "top"), "JP51": ("U40", "6", "top"), "R58": ("U40", "7", "bot"),
    "R59": ("U40", "6", "bot"), "C57": ("U40", "7", "bot"),
    "C58": ("U41", "3", "top"), "C59": ("U41", "3", "top"), "C60": ("U41", "5", "top"),
    "JP42": ("U41", "7", "top"), "JP52": ("U41", "6", "top"), "R60": ("U41", "7", "bot"),
    "R61": ("U41", "6", "bot"), "C61": ("U41", "7", "bot"),
    # connectors
    "R62": ("J34", "4", "bot"), "R63": ("J34", "5", "bot"),
    "R64": ("U50", "1", "top"), "R65": ("U50", "2", "top"), "R66": ("U50", "4", "top"),
    "R67": ("U50", "5", "top"), "R68": ("J36", "4", "top"),
    "R69": ("J37", "2", "bot"), "R70": ("J37", "3", "bot"), "R71": ("J37", "4", "bot"),
    "R72": ("J37", "5", "bot"), "R73": ("Q3", "1", "bot"), "R74": ("Q3", "1", "bot"),
}
TESTPOINTS_SIDE = "bot"
KEEP_CLEAR = [  # (x0, y0, x1, y1, side): no auto-placed parts here
    (93.0, 95.6, 107.0, 104.4, "bot"),   # IMU island (heater + IMUs + their caps only)
]
# Bottom-side band under the LQFP pin ring: vias cannot go there (MCU pads above), so only the
# VDD bypass caps that sit right on their pins may use it; everything else goes outside the ring.
RING_CLEAR = []  # tried a full band (91.3-108.7 minus 93.2-106.8): placement got too tight to route; kept off
RING_OK = {"C29", "C30", "C31", "C32", "C33", "C34", "C35", "C36", "C37", "C38", "C39", "C40", "C41"}
ISLAND_OK = {"U20", "U21", "C44", "C45", "C46", "C47", "C48", "R35", "R36", "R37",
             "R44", "R45", "R46", "R47"}


def load_netlist(path):
    root = parse(open(path).read())[0]
    comps = {}
    for c in find(find1(root, "components"), "comp"):
        ref = find1(c, "ref")[1]
        fields = {}
        fl = find1(c, "fields")
        if fl:
            for f in find(fl, "field"):
                nm = find1(f, "name")[1]
                fields[nm] = f[2] if len(f) > 2 and isinstance(f[2], str) else ""
        sp = find1(c, "sheetpath")
        comps[ref] = dict(ref=ref, value=find1(c, "value")[1], fp=find1(c, "footprint")[1] if find1(c, "footprint") else "",
                          fields=fields, path=find1(sp, "tstamps")[1] + find1(c, "tstamps")[1])
    nets = {}
    pinnet = {}
    for n in find(find1(root, "nets"), "net"):
        name = find1(n, "name")[1]
        for node in find(n, "node"):
            pinnet[(find1(node, "ref")[1], find1(node, "pin")[1])] = name
        nets[name] = [(find1(node, "ref")[1], find1(node, "pin")[1]) for node in find(n, "node")]
    return comps, nets, pinnet


def mm(v):
    return pcbnew.FromMM(v)


def vec(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def outline(board):
    r = CORNER_R
    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(vec(*a)); s.SetEnd(vec(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)
    def arc(c, start, mid, end):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(vec(*start), vec(*mid), vec(*end)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)
    seg((X0 + r, Y0), (X1 - r, Y0)); seg((X1, Y0 + r), (X1, Y1 - r))
    seg((X1 - r, Y1), (X0 + r, Y1)); seg((X0, Y1 - r), (X0, Y0 + r))
    k = r * (1 - math.sqrt(0.5))
    arc(None, (X1 - r, Y0), (X1 - k, Y0 + k), (X1, Y0 + r))
    arc(None, (X1, Y1 - r), (X1 - k, Y1 - k), (X1 - r, Y1))
    arc(None, (X0 + r, Y1), (X0 + k, Y1 - k), (X0, Y1 - r))
    arc(None, (X0, Y0 + r), (X0 + k, Y0 + k), (X0 + r, Y0))


def court_bbox(fp):
    """Courtyard bbox in mm (absolute), falling back to the footprint body."""
    layer = pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd
    fp.BuildCourtyardCaches()
    poly = fp.GetCourtyard(layer)
    if poly.OutlineCount():
        bb = poly.BBox()
        return (pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY()),
                pcbnew.ToMM(bb.GetX() + bb.GetWidth()), pcbnew.ToMM(bb.GetY() + bb.GetHeight()))
    bb = fp.GetBoundingBox(False, False)
    return (pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY()),
            pcbnew.ToMM(bb.GetX() + bb.GetWidth()), pcbnew.ToMM(bb.GetY() + bb.GetHeight()))


def place_fp(fp, x, y, rot, side):
    fp.SetPosition(vec(x, y))
    if side == "bot" and not fp.IsFlipped():
        fp.SetLayerAndFlip(pcbnew.B_Cu)
    fp.SetOrientationDegrees(rot)


def overlaps(a, b, gap=0.0):
    return a[0] < b[2] + gap and a[2] + gap > b[0] and a[1] < b[3] + gap and a[3] + gap > b[1]


def inside_board(bb, margin=0.3):
    if bb[0] < X0 + margin or bb[2] > X1 - margin or bb[1] < Y0 + margin or bb[3] > Y1 - margin:
        return False
    for hx in (CX - HOLE, CX + HOLE):
        for hy in (CY - HOLE, CY + HOLE):
            # distance from hole centre to the bbox
            dx = max(bb[0] - hx, 0, hx - bb[2]); dy = max(bb[1] - hy, 0, hy - bb[3])
            if math.hypot(dx, dy) < 3.05:
                return False
    return True


def main():
    comps, nets, pinnet = load_netlist(os.path.join(HERE, "fc.net"))
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(6)
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(6)
    netinfo = {}
    for name in sorted(nets):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    outline(board)
    fps = {}
    for ref, c in sorted(comps.items()):
        if not c["fp"]:
            continue
        lib, name = c["fp"].split(":")
        libdir = os.path.join(HERE, "kicad", "fc_custom.pretty") if lib == "fc_custom" else f"{KFP}/{lib}.pretty"
        fp = pcbnew.FootprintLoad(libdir, name)
        if fp is None:
            raise SystemExit(f"cannot load {c['fp']}")
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH(c["path"]))
        for k in ("LCSC",):
            if c["fields"].get(k):
                f = pcbnew.PCB_FIELD(fp, fp.GetNextFieldId(), k)
                f.SetText(c["fields"][k]); f.SetVisible(False); f.SetLayer(pcbnew.F_Fab)
                fp.AddField(f)
        for pad in fp.Pads():
            n = pinnet.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
        board.Add(fp)
        fps[ref] = fp
    # ---- fixed placement
    placed = {"top": [], "bot": []}
    for ref, (x, y, rot, side) in FIXED.items():
        if ref not in fps:
            continue
        place_fp(fps[ref], x, y, rot, side)
        placed[side].append((ref, court_bbox(fps[ref])))
    problems = []
    # Drilled holes block both sides: a part on the far side must not sit over a THT pad,
    # a thermal via array or an NPTH peg.
    def hole_boxes(ref):
        out = []
        for pad in fps[ref].Pads():
            if pad.HasHole():
                p = pad.GetPosition(); r = max(pcbnew.ToMM(pad.GetSize(pcbnew.F_Cu).x), pcbnew.ToMM(pad.GetSize(pcbnew.F_Cu).y),
                                                pcbnew.ToMM(pad.GetDrillSize().x)) / 2 + 0.2
                x, y = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
                out.append((x - r, y - r, x + r, y + r))
        return out
    for ref in list(FIXED):
        if ref in fps and not ref.startswith("H"):
            for hb in hole_boxes(ref):
                for side in ("top", "bot"):
                    for rb, b in placed[side]:
                        if rb.split("#")[0] != ref and overlaps(hb, b):
                            problems.append(f"hole of {ref} under {rb} ({side})")
                    placed[side].append((ref + "#hole", hb))
    for side in ("top", "bot"):
        for i, (ra, a) in enumerate(placed[side]):
            if not inside_board(a, 0.0) and not ra.startswith(("H", "J")):
                problems.append(f"{ra} outside board/hole keepout")
            for rb, b in placed[side][i + 1:]:
                if overlaps(a, b) and not (ra.startswith("H") or rb.startswith("H")) \
                        and ra.split("#")[0] != rb.split("#")[0]:
                    problems.append(f"fixed overlap {ra}/{rb} ({side})")
    # ---- rule-based placement
    def pad_xy(ref, num):
        for pad in fps[ref].Pads():
            if pad.GetNumber() == num:
                p = pad.GetPosition()
                return pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
        raise KeyError((ref, num))

    def try_place(ref, tx, ty, side, rots=(0, 90)):
        fp = fps[ref]
        best = None
        for rad in [i * 0.25 for i in range(0, 80)]:
            n = max(1, int(2 * math.pi * rad / 0.5))
            for k in range(n):
                ang = 2 * math.pi * k / n
                x = round((tx + rad * math.cos(ang)) / 0.05) * 0.05
                y = round((ty + rad * math.sin(ang)) / 0.05) * 0.05
                for rot in rots:
                    place_fp(fp, x, y, rot, side)
                    bb = court_bbox(fp)
                    if not inside_board(bb):
                        continue
                    if any(overlaps(bb, o) for _, o in placed[side]):
                        continue
                    if ref not in ISLAND_OK and any(
                            s == side and overlaps(bb, (k0, k1, k2, k3)) for k0, k1, k2, k3, s in KEEP_CLEAR):
                        continue
                    if side == "bot" and ref not in RING_OK and ref not in FIXED and any(overlaps(bb, r) for r in RING_CLEAR):
                        continue
                    best = (x, y, rot); break
                if best:
                    break
            if best:
                break
        if not best:
            problems.append(f"could not place {ref}")
            return
        place_fp(fp, *best, side)
        placed[side].append((ref, court_bbox(fp)))
        for hb in hole_boxes(ref):
            other = "bot" if side == "top" else "top"
            placed[other].append((ref + "#hole", hb))

    ANCHOR.update({k: v for k, v in IC_ANCHOR.items()})
    order = [r for r in IC_ANCHOR] + [r for r in ANCHOR if r not in IC_ANCHOR] + \
        sorted(r for r in fps if r not in ANCHOR and r not in FIXED)
    for ref in order:
        if ref not in fps or ref in FIXED:
            continue
        if ref in ANCHOR:
            aref, apad, side = ANCHOR[ref]
            tx, ty = pad_xy(aref, apad)
        else:
            # test points and anything else: near the first connected IC pad, bottom side
            side = TESTPOINTS_SIDE
            tx, ty = CX, CY + 14
            for pad in fps[ref].Pads():
                n = pad.GetNetname()
                cands = [(r, p) for r, p in nets.get(n, []) if r != ref and r[0] in "UJQ"]
                if cands:
                    tx, ty = pad_xy(*cands[0]); break
        try_place(ref, tx, ty, side)
    board.BuildConnectivity()
    out = os.path.join(HERE, "kicad", "fc.kicad_pcb")
    pcbnew.SaveBoard(out, board)
    print("saved", out, "footprints", len(fps))
    print("problems:", problems if problems else "none")
    json.dump({r: [round(pcbnew.ToMM(f.GetPosition().x), 3), round(pcbnew.ToMM(f.GetPosition().y), 3),
                   round(f.GetOrientationDegrees(), 1), "bot" if f.IsFlipped() else "top"] for r, f in fps.items()},
              open(os.path.join(HERE, "placement.json"), "w"), indent=0)


if __name__ == "__main__":
    main()
