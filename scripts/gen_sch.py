"""Write the KiCad 9 hierarchical schematic from design.py.

Every pin gets a short wire stub ending in a net label (local for nets that stay
on one sheet, global for nets that cross sheets) or a power symbol for rails.
That is the 'label style' many production schematics use: each sheet reads on
its own, and no wire crosses another.
"""
import copy, math, os, uuid, datetime
from sexp import parse, dump, find, find1, Sym
import design

S = Sym
KLIB = "/opt/r/usr/share/kicad/symbols/"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "kicad")
PROJECT = "fc"
GRID = 1.27
STUB = 2.54
CHAR_W = 1.05  # mm per character at 1.27 mm font
ROOT_UUID = str(uuid.uuid5(uuid.NAMESPACE_URL, "fc-root"))
REV = "B"
TITLE = "GPS-denied quadrotor flight controller"
DATE = datetime.date.today().isoformat()


def uid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "fc/" + "/".join(map(str, parts))))


def snap(v, g=GRID):
    return round(v / g) * g


# ---------------------------------------------------------------- libraries
_libcache = {}


def lib_symbols(libname):
    if libname not in _libcache:
        path = os.path.join(OUT, "fc_custom.kicad_sym") if libname == "fc_custom" else KLIB + libname + ".kicad_sym"
        root = parse(open(path).read())[0]
        _libcache[libname] = {s[1]: s for s in find(root, "symbol")}
    return _libcache[libname]


def flat_symbol(lib_id):
    """Return the symbol with 'extends' resolved, named 'Lib:Name' as schematics embed it."""
    libname, name = lib_id.split(":")
    syms = lib_symbols(libname)
    s = copy.deepcopy(syms[name])
    ext = find1(s, "extends")
    if ext:
        base = copy.deepcopy(syms[ext[1]])
        bname = base[1]
        props = {p[1]: p for p in find(s, "property")}
        out = [S("symbol"), name]
        for e in base[2:]:
            if isinstance(e, list) and e and e[0] == "property" and e[1] in props:
                out.append(props.pop(e[1]))
            elif isinstance(e, list) and e and e[0] == "symbol":
                e = copy.deepcopy(e)
                e[1] = e[1].replace(bname, name, 1)
                out.append(e)
            else:
                out.append(e)
        out[2:2] = []
        # remaining props only in derived
        idx = max(i for i, e in enumerate(out) if isinstance(e, list) and e and e[0] == "property")
        for p in props.values():
            idx += 1
            out.insert(idx, p)
        s = out
    s[1] = lib_id
    return s


def sym_pins(sym):
    pins = []

    def walk(n, unit):
        for e in n:
            if isinstance(e, list) and e and e[0] == "symbol":
                walk(e, e[1])
            elif isinstance(e, list) and e and e[0] == "pin":
                at = find1(e, "at")
                pins.append(dict(num=find1(e, "number")[1], name=find1(e, "name")[1], type=str(e[1]),
                                 x=float(at[1]), y=float(at[2]), ang=float(at[3]) if len(at) > 3 else 0.0,
                                 length=float(find1(e, "length")[1]), hidden=bool(find1(e, "hide"))))
    walk(sym, "")
    return pins


def sym_bbox(sym):
    xs, ys = [], []

    def walk(n):
        for e in n:
            if not isinstance(e, list) or not e:
                continue
            if e[0] in ("rectangle",):
                for k in ("start", "end"):
                    p = find1(e, k); xs.append(float(p[1])); ys.append(float(p[2]))
            elif e[0] == "polyline":
                for xy in find(find1(e, "pts"), "xy"):
                    xs.append(float(xy[1])); ys.append(float(xy[2]))
            elif e[0] == "circle":
                c = find1(e, "center"); r = float(find1(e, "radius")[1])
                xs.extend([float(c[1]) - r, float(c[1]) + r]); ys.extend([float(c[2]) - r, float(c[2]) + r])
            elif e[0] == "arc":
                for k in ("start", "mid", "end"):
                    p = find1(e, k)
                    if p: xs.append(float(p[1])); ys.append(float(p[2]))
            elif e[0] == "pin":
                at = find1(e, "at"); L = float(find1(e, "length")[1]); a = math.radians(float(at[3]))
                x, y = float(at[1]), float(at[2])
                xs.extend([x, x + L * math.cos(a)]); ys.extend([y, y + L * math.sin(a)])
            elif e[0] == "symbol":
                walk(e)
    walk(sym)
    if not xs:
        return (-1, -1, 1, 1)
    return (min(xs), min(ys), max(xs), max(ys))


def rot(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


# ---------------------------------------------------------------- items
def eff(size=1.27, justify=None, hide=False):
    e = [S("effects"), [S("font"), [S("size"), size, size]]]
    if justify:
        e.append([S("justify")] + [S(j) for j in justify.split()])
    if hide:
        e.append([S("hide"), S("yes")])
    return e


def wire(x1, y1, x2, y2, key):
    return [S("wire"), [S("pts"), [S("xy"), x1, y1], [S("xy"), x2, y2]],
            [S("stroke"), [S("width"), 0], [S("type"), S("default")]], [S("uuid"), uid("w", key)]]


def label(net, x, y, ang, key, glob):
    just = {0: "left bottom", 90: "left bottom", 180: "right bottom", 270: "right bottom"}[ang]
    if not glob:
        return [S("label"), net, [S("at"), x, y, ang], [S("fields_autoplaced"), S("yes")],
                eff(justify=just), [S("uuid"), uid("l", key)]]
    gj = {0: "left", 90: "left", 180: "right", 270: "right"}[ang]
    return [S("global_label"), net, [S("shape"), S("bidirectional")], [S("at"), x, y, ang],
            [S("fields_autoplaced"), S("yes")], eff(justify=gj), [S("uuid"), uid("g", key)],
            [S("property"), "Intersheetrefs", "${INTERSHEET_REFS}", [S("at"), x, y, ang],
             eff(size=1.27, justify=gj, hide=True)]]


def no_connect(x, y, key):
    return [S("no_connect"), [S("at"), x, y], [S("uuid"), uid("nc", key)]]


def text(t, x, y, key, size=1.27):
    return [S("text"), t, [S("exclude_from_sim"), S("no")], [S("at"), x, y, 0],
            eff(size=size, justify="left top"), [S("uuid"), uid("t", key)]]


def symbol_instance(lib_id, ref, value, fp, x, y, angle, props, pins, path, key, in_bom=True, unit=1):
    inst = [S("symbol"), [S("lib_id"), lib_id], [S("at"), x, y, angle], [S("unit"), unit],
            [S("exclude_from_sim"), S("no")], [S("in_bom"), S("yes" if in_bom else "no")],
            [S("on_board"), S("yes")], [S("dnp"), S("no")], [S("fields_autoplaced"), S("yes")],
            [S("uuid"), uid("s", key)]]
    for name, val, px, py, pa, hide, just in props:
        inst.append([S("property"), name, val, [S("at"), px, py, pa], eff(justify=just, hide=hide)])
    for p in sorted(set(pins)):
        inst.append([S("pin"), p, [S("uuid"), uid("p", key, p)]])
    inst.append([S("instances"), [S("project"), PROJECT, [S("path"), path, [S("reference"), ref],
                                                           [S("unit"), unit]]]])
    return inst


# ---------------------------------------------------------------- placement
def label_len(net, glob):
    return len(net) * CHAR_W * 1.05 + (6.0 if glob else 1.8)


def part_geometry(p, sym, angle):
    pins = sym_pins(sym)
    x0, y0, x1, y1 = sym_bbox(sym)
    corners = [rot(x, y, angle) for x, y in [(x0, y0), (x0, y1), (x1, y0), (x1, y1)]]
    bx0 = min(c[0] for c in corners); bx1 = max(c[0] for c in corners)
    by0 = min(-c[1] for c in corners); by1 = max(-c[1] for c in corners)
    out = []
    for pn in pins:
        rx, ry = rot(pn["x"], pn["y"], angle)
        out.append(dict(pn, sx=rx, sy=-ry, out=(pn["ang"] + angle + 180) % 360))
    return out, [bx0, by0, bx1, by1]


def clusters(p, pins):
    """Group a part's connected pins that share a net and point the same way, so e.g. two GND
    pins get one ground symbol joined by a short wire instead of two overlapping symbols."""
    seen = {}
    groups = {}
    for pn in pins:
        net = p["pins"].get(pn["num"])
        pos = (round(pn["sx"], 2), round(pn["sy"], 2))
        if pos in seen:
            if seen[pos] != net:
                raise SystemExit(f"{p['ref']} stacked pins at {pos} on different nets")
            continue
        seen[pos] = net
        if net is None:
            continue
        o = int(round(pn["out"])) % 360
        axis = round(pn["sx"], 2) if o in (0, 180) else round(pn["sy"], 2)
        groups.setdefault((net, o, axis), []).append(pn)
    return groups


def part_extent(p, pins, bb, multi):
    ext = list(bb)
    for (net, o, axis), pns in clusters(p, pins).items():
        glob = net in multi
        L = STUB + (7.0 if net in design.RAILS else label_len(net, glob))
        for pn in pns:
            ex = pn["sx"] + L * math.cos(math.radians(o))
            ey = pn["sy"] - L * math.sin(math.radians(o))
            ext[0] = min(ext[0], ex); ext[2] = max(ext[2], ex)
            ext[1] = min(ext[1], ey - 1.6); ext[3] = max(ext[3], ey + 1.6)
        if net in design.RAILS and o in (0, 180):
            for pn in pns:
                L2 = (2 * STUB if len(pns) > 1 else STUB) + 3.5 + len(net) * CHAR_W
                ex = pn["sx"] + L2 * (1 if o == 0 else -1)
                ext[0] = min(ext[0], ex); ext[2] = max(ext[2], ex)
    tw = max(len(p["value"]), len(p["ref"])) * CHAR_W / 2 + 1
    cx = (bb[0] + bb[2]) / 2
    ext[0] = min(ext[0], cx - tw); ext[2] = max(ext[2], cx + tw)
    ext[1] -= 3.2; ext[3] += 3.2
    return ext


def orient(p, sym):
    npins = len({pn["num"] for pn in sym_pins(sym)})
    if npins == 2 and p["lib"].split(":")[0] in ("Device", "Jumper") and \
            p["lib"] not in ("Device:D_Zener", "Device:D_Schottky", "Device:LED"):
        return 90
    return 0


def shelf(boxes, max_w, gap_x, gap_y):
    """boxes: list of (w, h). Returns positions (x, y) of top-left corners and total size."""
    x = y = row_h = 0.0
    pos, W = [], 0.0
    for w, h in boxes:
        if x > 0 and x + w > max_w:
            x = 0; y += row_h + gap_y; row_h = 0
        pos.append((x, y))
        x += w + gap_x; row_h = max(row_h, h); W = max(W, x - gap_x)
    return pos, W, y + row_h


PAGES = [("A3", 420, 297), ("A2", 594, 420), ("A1", 841, 594)]


def plan_sheet(sheet_key, parts, multi):
    syms_used = {}
    groups = []
    for p in parts:
        if not groups or groups[-1][0] != p["group"]:
            groups.append((p["group"], []))
        sym = flat_symbol(p["lib"])
        syms_used[p["lib"]] = sym
        angle = orient(p, sym)
        pins, bb = part_geometry(p, sym, angle)
        ext = part_extent(p, pins, bb, multi)
        groups[-1][1].append((p, sym, angle, pins, ext))
    margin_x, margin_top, margin_bot = 12.7, 15.24, 12.0
    notes_lines = SHEET_NOTES.get(sheet_key, "").count("\n") + 1 if SHEET_NOTES.get(sheet_key) else 0

    def collides(gpos, gboxes, pw, ph):
        keepouts = [(pw - 190, ph - 50, pw, ph)]  # title block
        if notes_lines:
            keepouts.append((0, ph - 14 - notes_lines * 2.6, pw - 190, ph))
        for (gx, gy), (gw, gh) in zip(gpos, gboxes):
            x0, y0, x1, y1 = margin_x + gx, margin_top + gy, margin_x + gx + gw, margin_top + gy + gh
            if y1 > ph - margin_bot:
                return True
            for kx0, ky0, kx1, ky1 in keepouts:
                if x0 < kx1 and x1 > kx0 and y0 < ky1 and y1 > ky0:
                    return True
        return False

    found = None
    for paper, pw, ph in PAGES:
        for widen in (90, 140, 200, 60):
            gboxes, inner = [], []
            for name, members in groups:
                first_w = members[0][4][2] - members[0][4][0]
                max_w = max(first_w + widen, 140)
                boxes = [(e[2] - e[0] + 2.54, e[3] - e[1]) for (_, _, _, _, e) in members]
                pos, W, H = shelf(boxes, max_w, 2.54, 2.54)
                W = max(W, len(name) * 1.3 + 4)
                inner.append(pos)
                gboxes.append((W + 6, H + 9))
            for order in ("design", "tall-first"):
                idx = list(range(len(groups)))
                if order == "tall-first":
                    idx.sort(key=lambda i: -gboxes[i][1])
                gpos_o, GW, GH = shelf([gboxes[i] for i in idx], pw - 2 * margin_x, 6, 6)
                gpos = [None] * len(groups)
                for k, i in enumerate(idx):
                    gpos[i] = gpos_o[k]
                if not collides(gpos, gboxes, pw, ph):
                    found = (paper, pw, ph, gpos, gboxes, inner)
                    break
            if found:
                break
        if found:
            break
    if not found:
        raise SystemExit(f"{sheet_key}: does not fit on A1")
    paper, pw, ph, gpos, gboxes, inner = found
    placements, frames = [], []
    for (name, members), (gx, gy), pos, (gw, gh) in zip(groups, gpos, inner, gboxes):
        fx, fy = margin_x + gx, margin_top + gy
        frames.append((name, fx, fy, fx + gw, fy + gh))
        for (p, sym, angle, pins, ext), (px, py) in zip(members, pos):
            ox = snap(fx + 3 + px - ext[0], 2.54)
            oy = snap(fy + 7 + py - ext[1], 2.54)
            placements.append((p, sym, angle, pins, ox, oy, ext))
    return placements, frames, syms_used, (paper, pw, ph)


def junction(x, y, key):
    return [S("junction"), [S("at"), x, y], [S("diameter"), 0], [S("color"), 0, 0, 0, 0],
            [S("uuid"), uid("j", key)]]


def frame(name, x0, y0, x1, y1, key):
    return [[S("rectangle"), [S("start"), x0, y0], [S("end"), x1, y1],
             [S("stroke"), [S("width"), 0.15], [S("type"), S("dash")], [S("color"), 120, 120, 120, 1]],
             [S("fill"), [S("type"), S("none")]], [S("uuid"), uid("fr", key)]],
            [S("text"), name, [S("exclude_from_sim"), S("no")], [S("at"), x0 + 1.5, y0 + 1.5, 0],
             [S("effects"), [S("font"), [S("size"), 1.6, 1.6], [S("thickness"), 0.3], [S("bold"), S("yes")]],
              [S("justify"), S("left"), S("top")]], [S("uuid"), uid("frt", key)]]]


def emit_sheet(sheet_key, title, parts, multi, path, page_no):
    placements, frames, syms_used, (paper, pw, ph) = plan_sheet(sheet_key, parts, multi)
    items = []
    pwr_n = [0]
    for i, f in enumerate(frames):
        items += frame(f[0], *f[1:], f"{sheet_key}/{i}")

    def power_sym(net, x, y, outward, key):
        pwr_n[0] += 1
        lib_id = "power:GND" if net == "GND" else ("power:+5V" if net == "+5V" else
                                                    "power:+3V3" if net == "+3V3" else f"fc_custom:{net}")
        sym = flat_symbol(lib_id)
        syms_used[lib_id] = sym
        if outward in (0, 180):
            # sideways arrow keeps the rail name in the pin's own row
            angle = (outward - 270) % 360 if net == "GND" else (outward - 90) % 360
            d = 1 if outward == 0 else -1
            vy = y
        elif net == "GND":
            angle = 180 if outward == 90 else 0      # normally points down
            vy = y + 3.81 if angle == 0 else y - 3.81
        else:
            angle = 180 if outward == 270 else 0     # normally points up
            vy = y - 3.556 if angle == 0 else y + 3.556
        ref = f"#PWR0{sheet_key[:2].upper()}{pwr_n[0]:03d}"
        vj, vx = None, x
        if outward in (0, 180):
            off = 3.6 + len(net) * CHAR_W * 0.5
            vx = x + (off if outward == 0 else -off)
        props = [("Reference", ref, x, y, angle, True, None),
                 ("Value", net, vx, vy, angle, False, vj),
                 ("Footprint", "", x, y, 0, True, None), ("Datasheet", "", x, y, 0, True, None),
                 ("Description", "", x, y, 0, True, None)]
        items.append(symbol_instance(lib_id, ref, net, "", x, y, angle, props, ["1"], path, key, in_bom=False))

    for p, sym, angle, pins, ox, oy, ext in placements:
        ref = p["ref"]
        lp = {e[1]: e for e in find(sym, "property")}
        isflag = p["lib"] == "power:PWR_FLAG"
        if angle in (90, 270):
            rpos, vpos, rj, vj = (ox, oy - 2.54), (ox, oy + 2.54), None, None
            _, bb = part_geometry(p, sym, angle)
            rpos = (ox, oy + bb[1] - 1.4); vpos = (ox, oy + bb[3] + 1.4)
        else:
            r_at = lp["Reference"][3]; v_at = lp["Value"][3]
            rpos = (ox + float(r_at[1]), oy - float(r_at[2]))
            vpos = (ox + float(v_at[1]), oy - float(v_at[2]))

            def j(e):
                jj = find1(find1(e, "effects"), "justify")
                return " ".join(map(str, jj[1:])) if jj else None
            rj, vj = j(lp["Reference"]), j(lp["Value"])
        if isflag:
            ref = f"#FLG0{sheet_key[:2].upper()}{ref[4:]}"
        fa = angle  # KiCad draws field angles relative to the symbol; this keeps text horizontal
        props = [("Reference", ref, rpos[0], rpos[1], fa, isflag, rj),
                 ("Value", p["value"], vpos[0], vpos[1], fa, False, vj),
                 ("Footprint", p["fp"], ox, oy, 0, True, None),
                 ("Datasheet", "", ox, oy, 0, True, None),
                 ("Description", p.get("note") or "", ox, oy, 0, True, None)]
        if not isflag:
            props.append(("LCSC", p.get("lcsc", ""), ox, oy, 0, True, None))
        if p.get("rating"):
            props.append(("Rating", p["rating"], ox, oy, 0, True, None))
        in_bom = not (isflag or p["ref"].startswith(("H", "FID", "TP", "JP")))
        items.append(symbol_instance(p["lib"], ref, p["value"], p["fp"], ox, oy, angle, props,
                                     [pn["num"] for pn in pins], path, f"{sheet_key}/{ref}", in_bom=in_bom))
        # unconnected pins
        seen = set()
        for pn in pins:
            if pn["num"] not in p["pins"] and pn["type"] != "no_connect":
                raise SystemExit(f"{ref} pin {pn['num']} ({pn['name']}) missing from design.py")
            pos = (round(pn["sx"], 2), round(pn["sy"], 2))
            if p["pins"].get(pn["num"]) is None and pos not in seen:
                items.append(no_connect(snap(ox + pn["sx"], 0.01), snap(oy + pn["sy"], 0.01),
                                        f"{sheet_key}/{ref}/{pn['num']}"))
            seen.add(pos)
        for (net, o, axis), pns in clusters(p, pins).items():
            key = f"{sheet_key}/{ref}/{pns[0]['num']}"
            dx, dy = round(math.cos(math.radians(o))), -round(math.sin(math.radians(o)))
            ends = []
            for pn in pns:
                x, y = snap(ox + pn["sx"], 0.01), snap(oy + pn["sy"], 0.01)
                ex, ey = x + dx * STUB, y + dy * STUB
                items.append(wire(x, y, ex, ey, f"{key}/{pn['num']}"))
                ends.append((ex, ey))
            # join the stub ends; pick the end nearest the outside edge for the label
            ends.sort(key=lambda e: (e[1], e[0]))
            for a, b in zip(ends, ends[1:]):
                items.append(wire(a[0], a[1], b[0], b[1], f"{key}/join{a}"))
            for e in ends[1:-1]:
                items.append(junction(e[0], e[1], f"{key}/jn{e}"))
            if len(ends) > 1:
                # label/power symbol hangs off the first end, through one more stub
                lx, ly = ends[0]
                if o in (0, 180):  # stubs horizontal -> joined vertically -> extend from top end
                    items.append(junction(lx, ly, f"{key}/jt"))
                ex, ey = lx + dx * STUB, ly + dy * STUB
                items.append(wire(lx, ly, ex, ey, f"{key}/ext"))
                lx, ly = ex, ey
            else:
                lx, ly = ends[0]
            if net in design.RAILS:
                power_sym(net, lx, ly, o, key + "/pwr")
            else:
                items.append(label(net, lx, ly, o, key + "/lbl", net in multi))
    notes = SHEET_NOTES.get(sheet_key)
    if notes:
        items.append(text(notes, 15, ph - 12 - (notes.count("\n") + 1) * 2.6, f"{sheet_key}/notes", 1.5))
    sch = [S("kicad_sch"), [S("version"), 20250114], [S("generator"), "eeschema"],
           [S("generator_version"), "9.0"], [S("uuid"), uid("file", sheet_key)],
           [S("paper"), paper], title_block(title, page_no),
           [S("lib_symbols")] + list(syms_used.values())] + items + [[S("embedded_fonts"), S("no")]]
    with open(os.path.join(OUT, f"{sheet_key}.kicad_sch"), "w") as fh:
        fh.write(dump(sch) + "\n")
    return len([p for p in placements if p[0]["lib"] != "power:PWR_FLAG"])


def title_block(sub, page):
    return [S("title_block"), [S("title"), f"{TITLE}: {sub}"], [S("date"), DATE], [S("rev"), REV],
            [S("company"), "Daniel K (dvntekim)"],
            [S("comment"), 1, "DRAFT UNTIL INDEPENDENT REVIEW. Not for fabrication."],
            [S("comment"), 2, "Pin map: PX4 FMUv6C (Pixhawk 6C) derivative, STM32H743VIT6 LQFP-100"],
            [S("comment"), 3, "Generated from design.py; edit the source, not this file"]]


SHEET_NOTES = {
    "power": ("Power tree: VBAT (2S-6S) -> RPP P-FET -> TVS -> TPS54360B buck (+5V, 3.5 A, 597 kHz).\n"
              "+5V -> LM66100 ideal diode -> +5V_FMU (USB backs it up through a second LM66100 that the buck overrides).\n"
              "+5V_FMU -> TLV62569 -> +3V3 (MCU, SD, CAN VIO);  +5V_FMU -> LP5907 -> +3V3_SENS (IMUs, baro; MCU-switchable).\n"
              "+5V -> TPS2553 x2 -> +5V_PERIPH (UARTs, 1.2 A) and +5V_CAN (1.0 A): a shorted cable trips its own switch.\n"
              "Compensation values are checked in sim/buck (ngspice)."),
    "mcu": ("STM32H743VIT6. Pin map follows PX4 FMUv6C; see pinmap.md for every pin's alternate-function check.\n"
            "Decoupling per ST AN4938: 100 nF per VDD pin + 4.7 uF bulk, 2.2 uF per VCAP, VDDA through a ferrite.\n"
            "BOOT0 bridge enters ST ROM DFU on a blank chip. SCK/CLK series resistors sit at the MCU."),
    "sensors": ("ICM-45686 on SPI1 with a 32 kHz CLKIN from TIM2_CH3 (PX4: icm45686 -C 32000), BMI088 on SPI2 (different vendor, own bus).\n"
                "BMP581 on I2C4 at 0x47. All sensors on +3V3_SENS, which the MCU can power-cycle.\n"
                "Heater: 4 x 120R around the IMUs, AO3400A on TIM17_CH1 (PX4 heater driver holds IMU temperature)."),
    "storage_usb": "microSD on SDMMC2 (4-bit). USB-C device with 5.1k Rd, USBLC6 ESD, VBUS sense to PA9.",
    "can": ("Two TCAN1462V CAN FD transceivers (8 Mbit/s, signal improvement). CAN1: DroneCAN flow + ToF. CAN2: reserved for own ESC.\n"
            "Split termination is bridged by default; cut JP4x/JP5x when the FC is not a bus end."),
    "connectors": ("Pixhawk-standard JST-GH for peripherals, JST-SH for ESC and debug (DS-009).\n"
                   "AUX: M7 = camera trigger, M8 = camera capture for hardware time sync with a VIO camera."),
}


def emit_root(sheets):
    items = []
    x, y = 30, 40
    w, h = 60, 25
    for i, (key, title, n) in enumerate(sheets):
        sx = x + (i % 3) * (w + 25)
        sy = y + (i // 3) * (h + 25)
        items.append([S("sheet"), [S("at"), sx, sy], [S("size"), w, h], [S("exclude_from_sim"), S("no")],
                      [S("in_bom"), S("yes")], [S("on_board"), S("yes")], [S("dnp"), S("no")],
                      [S("fields_autoplaced"), S("yes")],
                      [S("stroke"), [S("width"), 0.1524], [S("type"), S("solid")]],
                      [S("fill"), [S("color"), 0, 0, 0, 0.0]], [S("uuid"), uid("sheet", key)],
                      [S("property"), "Sheetname", title, [S("at"), sx, sy - 0.7, 0], eff(justify="left bottom")],
                      [S("property"), "Sheetfile", f"{key}.kicad_sch", [S("at"), sx, sy + h + 0.6, 0],
                       eff(justify="left top")],
                      [S("instances"), [S("project"), PROJECT, [S("path"), f"/{ROOT_UUID}",
                                                                 [S("page"), str(i + 2)]]]]])
        items.append(text(f"{n} parts", sx + 2, sy + 5, f"root/n/{key}"))
    overview = (
        f"GPS-denied quadrotor flight controller, rev {REV} (DRAFT UNTIL INDEPENDENT REVIEW)\n\n"
        "MCU: STM32H743VIT6, 480 MHz Cortex-M7, PX4 (NuttX). Pin map derived from Pixhawk FMUv6C.\n"
        "IMUs: ICM-45686 (SPI1, external 32 kHz clock) + BMI088 (SPI2). Baro: BMP581 (I2C4). IMU heater on an isolated island (rev B).\n"
        "Storage: microSD (SDMMC2) for logs, params and the RAPTOR policy.\n"
        "Buses: 2x CAN FD (TCAN1462V), TELEM1/TELEM2 with flow control, GPS/I2C, RC (CRSF), USB-C.\n"
        "Motors: M1-M4 on TIM1 (bidirectional DShot) via 8-pin ESC harness with telemetry and current; M5-M8 on AUX.\n"
        "Power: 2S-6S in, reverse-polarity FET, TVS, 5 V 3.5 A buck, ideal-diode USB backup, 3V3 buck, low-noise sensor LDO,\n"
        "current-limited peripheral and CAN power.\n"
        "Board: 38 x 38 mm, 30.5 mm M3 mount, 6-layer JLCPCB.")
    items.append(text(overview, 30, 130, "root/overview", 1.8))
    sch = [S("kicad_sch"), [S("version"), 20250114], [S("generator"), "eeschema"],
           [S("generator_version"), "9.0"], [S("uuid"), ROOT_UUID], [S("paper"), "A3"],
           title_block("Overview", 1), [S("lib_symbols")]] + items + \
          [[S("sheet_instances"), [S("path"), "/", [S("page"), "1"]]], [S("embedded_fonts"), S("no")]]
    with open(os.path.join(OUT, f"{PROJECT}.kicad_sch"), "w") as fh:
        fh.write(dump(sch) + "\n")


def emit_project():
    import json
    pro = {
        "board": {"design_settings": {}},
        "boards": [],
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": f"{PROJECT}.kicad_pro", "version": 3},
        "erc": {"erc_exclusions": [], "meta": {"version": 0}, "pin_map": [], "rule_severities": {}},
        "net_settings": {"classes": [{"name": "Default", "clearance": 0.1, "track_width": 0.127,
                                      "via_diameter": 0.45, "via_drill": 0.2, "diff_pair_width": 0.127,
                                      "diff_pair_gap": 0.127, "wire_width": 6, "bus_width": 12,
                                      "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)",
                                      "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647}],
                         "meta": {"version": 4}},
        "schematic": {"meta": {"version": 1}},
        "sheets": [[ROOT_UUID, "Root"]] + [[uid("sheet", k), t] for k, t in design.SHEETS],
        "text_variables": {"REV": REV},
    }
    ncp = os.path.join(HERE, "netclasses.json")
    if os.path.exists(ncp):
        pro["net_settings"] = json.load(open(ncp))
    with open(os.path.join(OUT, f"{PROJECT}.kicad_pro"), "w") as fh:
        json.dump(pro, fh, indent=2)
    with open(os.path.join(OUT, "sym-lib-table"), "w") as fh:
        fh.write('(sym_lib_table\n  (version 7)\n  (lib (name "fc_custom")(type "KiCad")(uri "${KIPRJMOD}/fc_custom.kicad_sym")(options "")(descr "Project symbols"))\n)\n')
    with open(os.path.join(OUT, "fp-lib-table"), "w") as fh:
        fh.write('(fp_lib_table\n  (version 7)\n  (lib (name "fc_custom")(type "KiCad")(uri "${KIPRJMOD}/fc_custom.pretty")(options "")(descr "Project footprints"))\n)\n')


def main():
    nets_by_sheet = {}
    for p in design.PARTS:
        for n in p["pins"].values():
            if n:
                nets_by_sheet.setdefault(n, set()).add(p["sheet"])
    multi = {n for n, s in nets_by_sheet.items() if len(s) > 1}
    # every net that touches the MCU is drawn as a global label so the MCU sheet reads uniformly
    mcu = next(p for p in design.PARTS if p["ref"] == "U10")
    multi |= {n for n in mcu["pins"].values() if n}
    # uniform style: every signal net is a global label (rails are power symbols)
    multi |= set(nets_by_sheet)
    counts = []
    for i, (key, title) in enumerate(design.SHEETS):
        parts = [p for p in design.PARTS if p["sheet"] == key]
        path = f"/{ROOT_UUID}/{uid('sheet', key)}"
        n = emit_sheet(key, title, parts, multi, path, i + 2)
        counts.append((key, title, n))
    emit_root(counts)
    emit_project()
    print("sheets:", counts)


if __name__ == "__main__":
    main()
