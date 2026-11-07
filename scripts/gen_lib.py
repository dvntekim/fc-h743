"""Generate the project symbol library (fc_custom.kicad_sym) and footprint
library (fc_custom.pretty) for parts KiCad's stock libraries don't cover.

Every pin number and land pattern below is copied from the manufacturer's
datasheet (section noted next to each item); see docs/footprint-sources.md.
"""
import copy, math, os, uuid
from sexp import parse, dump, find, find1, Sym

KLIB = "/opt/r/usr/share/kicad/symbols/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kicad")
S = Sym


def font(size=1.27):
    return [S("effects"), [S("font"), [S("size"), size, size]]]


def prop(name, value, x=0.0, y=0.0, hide=False, justify=None):
    eff = font()
    if justify:
        eff.append([S("justify"), S(justify)])
    if hide:
        eff.append([S("hide"), S("yes")])
    return [S("property"), name, value, [S("at"), x, y, 0], eff]


def pin(num, name, typ, x, y, ang, length=2.54, hide=False):
    p = [S("pin"), S(typ), S("line"), [S("at"), x, y, ang], [S("length"), length]]
    if hide:
        p.append([S("hide"), S("yes")])
    p += [[S("name"), name, font()], [S("number"), str(num), font()]]
    return p


def box_symbol(name, ref, left, right, top, bottom, width=15.24, desc="", fp="", ds=""):
    """left/right: list of (num, name, type) from top to bottom; top/bottom: left to right.
    None entries leave a gap. The box grows so pin names never overlap."""
    nm = lambda lst: max([len(p[1].replace("~{", "").replace("}", "")) for p in lst if p] or [0])
    n_side = max(len(left), len(right))
    vert = max(nm(top), nm(bottom)) * 1.0
    h = (n_side + 1) * 2.54 + 2 * max(0, vert - 1.27)
    h = max(math.ceil(h / 2.54) * 2.54, 10.16)
    w = max(width, (nm(left) + nm(right)) * 1.05 + 5.08, (max(len(top), len(bottom)) + 1) * 2.54)
    w = math.ceil(w / 5.08) * 5.08
    top_y = math.ceil((h / 2) / 2.54) * 2.54
    bot_y = top_y - h
    pad = math.ceil(max(0, vert - 1.27) / 2.54) * 2.54
    top_y_pins = top_y - pad
    pins = []
    for i, p in enumerate(left):
        if p:
            pins.append(pin(p[0], p[1], p[2], -w / 2 - 2.54, top_y_pins - 2.54 * (i + 1), 0))
    for i, p in enumerate(right):
        if p:
            pins.append(pin(p[0], p[1], p[2], w / 2 + 2.54, top_y_pins - 2.54 * (i + 1), 180))
    def spread(lst):
        n = len(lst)
        x0 = -2.54 * (n - 1) / 2
        x0 = round(x0 / 2.54) * 2.54
        return [(x0 + 2.54 * i, p) for i, p in enumerate(lst)]
    for x, p in spread(top):
        if p:
            pins.append(pin(p[0], p[1], p[2], x, top_y + 2.54, 270))
    for x, p in spread(bottom):
        if p:
            pins.append(pin(p[0], p[1], p[2], x, bot_y - 2.54, 90))
    sym = [S("symbol"), name,
           [S("pin_names"), [S("offset"), 1.016]],
           [S("exclude_from_sim"), S("no")], [S("in_bom"), S("yes")], [S("on_board"), S("yes")],
           prop("Reference", ref, -w / 2, top_y + 1.27, justify="left bottom"),
           prop("Value", name, w / 2, bot_y - 1.27, justify="right top"),
           prop("Footprint", fp, 0, 0, hide=True),
           prop("Datasheet", ds, 0, 0, hide=True),
           prop("Description", desc, 0, 0, hide=True),
           [S("symbol"), f"{name}_0_1",
            [S("rectangle"), [S("start"), -w / 2, top_y], [S("end"), w / 2, bot_y],
             [S("stroke"), [S("width"), 0.254], [S("type"), S("default")]],
             [S("fill"), [S("type"), S("background")]]]],
           [S("symbol"), f"{name}_1_1"] + pins,
           [S("embedded_fonts"), S("no")]]
    return sym


def load(lib, name):
    root = parse(open(KLIB + lib + ".kicad_sym").read())[0]
    return {s[1]: s for s in find(root, "symbol")}[name]


def renamed(sym, new):
    s = copy.deepcopy(sym)
    old = s[1]
    s[1] = new
    for e in s:
        if isinstance(e, list) and e and e[0] == "symbol":
            e[1] = e[1].replace(old, new, 1)
        if isinstance(e, list) and e and e[0] == "property" and e[1] == "Value":
            e[2] = new
    return s


def power_symbol(net):
    s = renamed(load("power", "+5V"), net)
    for e in s:
        if isinstance(e, list) and e and e[0] == "property" and e[1] == "Description":
            e[2] = f'Power symbol creates a global label with name "{net}"'
    return s


def pmos_powerdi():
    """DMP4013LFGQ: PowerDI3333-8, pins 1-3 S, 4 G, 5-8 + pad D (Diodes Inc. datasheet, Pin Description)."""
    s = renamed(load("Device", "Q_PMOS"), "DMP4013LFGQ")
    for e in s:
        if isinstance(e, list) and e and e[0] == "symbol" and e[1].endswith("_1_1"):
            newpins = []
            for p in [x for x in e if isinstance(x, list) and x and x[0] == "pin"]:
                nm = find1(p, "name")[1]
                numnode = find1(p, "number")
                if nm == "S":
                    for i, n in enumerate(["1", "2", "3"]):
                        q = copy.deepcopy(p)
                        find1(q, "number")[1] = n
                        if i:
                            q.insert(4, [S("hide"), S("yes")])
                            q[1] = S("passive")
                        newpins.append(q)
                elif nm == "G":
                    numnode[1] = "4"; newpins.append(p)
                elif nm == "D":
                    numnode[1] = "5"; newpins.append(p)
            e[:] = [x for x in e if not (isinstance(x, list) and x and x[0] == "pin")] + newpins
        if isinstance(e, list) and e and e[0] == "property" and e[1] == "Footprint":
            e[2] = "Package_SON:Diodes_PowerDI3333-8"
        if isinstance(e, list) and e and e[0] == "property" and e[1] == "Description":
            e[2] = "P-MOSFET -40 V 10.3 A, 18 mOhm @ 4.5 V, PowerDI3333-8"
    return s


def lm66100_or():
    """LM66100 with VOUT as passive so two ideal diodes can OR into one rail without an ERC
    power-output conflict (TI SLVSEZ8A, Pin Functions)."""
    s = renamed(load("Power_Management", "LM66100DCK"), "LM66100")
    for e in s:
        if isinstance(e, list) and e and e[0] == "symbol":
            for p in e:
                if isinstance(p, list) and p and p[0] == "pin" and find1(p, "name")[1] == "VOUT":
                    p[1] = S("passive")
    return s


def bmi088_tristate():
    """BMI088 with SDO1/SDO2 as tri-state: they share MISO and only drive while their CS is low
    (Bosch BST-BMI088-DS001, section 6.1)."""
    s = renamed(load("Sensor_Motion", "BMI088"), "BMI088")
    for e in s:
        if isinstance(e, list) and e and e[0] == "symbol":
            for p in e:
                if isinstance(p, list) and p and p[0] == "pin" and find1(p, "name")[1].startswith("SDO"):
                    p[1] = S("tri_state")
    return s


def symbols():
    syms = [
        # TDK DS-000489 rev 1.1, section 4.1 / Figure 4
        box_symbol("ICM-45686", "U",
                   left=[(13, "SCLK", "input"), (14, "SDI", "input"), (1, "SDO", "output"),
                         (12, "~{CS}", "input"), None, (2, "RESV", "no_connect"),
                         (3, "RESV", "no_connect")],
                   right=[(4, "INT1", "output"), (9, "CLKIN", "bidirectional"), None,
                          (7, "RESV", "no_connect"), (10, "RESV", "no_connect"),
                          (11, "RESV", "no_connect")],
                   top=[(8, "VDD", "power_in"), (5, "VDDIO", "power_in")],
                   bottom=[(6, "GND", "power_in")], width=20.32,
                   desc="6-axis IMU, BalancedGyro, SPI/I3C, external clock input",
                   fp="Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y"),
        # Bosch BST-BMP581-DS004-13, Table 28
        box_symbol("BMP581", "U",
                   left=[(2, "SCK", "input"), (4, "SDI", "bidirectional"), (5, "SDO", "bidirectional"),
                         (6, "CSB", "input")],
                   right=[(7, "INT", "output")],
                   top=[(10, "VDD", "power_in"), (1, "VDDIO", "power_in")],
                   bottom=[(3, "VSS", "power_in"), (8, "VSS", "passive"), (9, "VSS", "passive")],
                   width=12.7, desc="Barometric pressure sensor, 0.1 Pa RMS",
                   fp="fc_custom:Bosch_LGA-10_2x2mm_P0.5mm_BMP581"),
        # TI ZHCSQR4A (TCAN1462-Q1), Table 7-1
        box_symbol("TCAN1462V", "U",
                   left=[(1, "TXD", "input"), (4, "RXD", "output"), (8, "STB", "input")],
                   right=[(7, "CANH", "bidirectional"), (6, "CANL", "bidirectional")],
                   top=[(3, "VCC", "power_in"), (5, "VIO", "power_in")],
                   bottom=[(2, "GND", "power_in"), (9, "EP", "passive")],
                   width=12.7, desc="CAN FD transceiver with SIC, 8 Mbit/s, VIO",
                   fp="fc_custom:TI_DRB0008J_VSON-8_3x3mm_P0.65mm"),
        # TI SLVS841E, Pin Functions (DBV)
        box_symbol("TPS2553", "U",
                   left=[(1, "IN", "power_in"), (3, "EN", "input")],
                   right=[(6, "OUT", "power_out"), (4, "~{FAULT}", "open_collector"), (5, "ILIM", "passive")],
                   top=[], bottom=[(2, "GND", "power_in")], width=17.78,
                   desc="Current-limited power switch, adjustable limit, active-high EN",
                   fp="Package_TO_SOT_SMD:SOT-23-6"),
        # TI SBOS493 (TMP302), Pin Functions (DRL)
        box_symbol("TMP302", "U",
                   left=[(1, "TRIPSET0", "input"), (6, "TRIPSET1", "input"), (4, "HYSTSET", "input")],
                   right=[(3, "~{OUT}", "open_collector")],
                   top=[(5, "VS", "power_in")], bottom=[(2, "GND", "power_in")], width=15.24,
                   desc="Temperature switch, open-drain active-low output, trip 50-65 C (A grade)",
                   fp="Package_TO_SOT_SMD:SOT-563"),
        pmos_powerdi(),
        lm66100_or(),
        bmi088_tristate(),
    ]
    rails = ["VBAT_RAW", "VBAT", "+5V_FMU", "+5V_PERIPH", "+5V_CAN", "+3V3_SENS", "VDDA",
             "USB_VBUS", "USB_VBUS_F"]
    syms += [power_symbol(r) for r in rails]
    lib = [S("kicad_symbol_lib"), [S("version"), 20241209], [S("generator"), "fc_gen"],
           [S("generator_version"), "9.0"]] + syms
    with open(os.path.join(OUT, "fc_custom.kicad_sym"), "w") as f:
        f.write(dump(lib) + "\n")
    return syms


# ----------------------------- footprints -----------------------------
def fp_text(kind, txt, x, y, layer, hide=False):
    e = [S("property"), kind, txt, [S("at"), x, y, 0], [S("layer"), layer],
         [S("uuid"), str(uuid.uuid4())],
         [S("effects"), [S("font"), [S("size"), 0.8, 0.8], [S("thickness"), 0.12]]]]
    if hide:
        e.insert(5, [S("hide"), S("yes")])
    return e


def line(x1, y1, x2, y2, layer, w=0.12):
    return [S("fp_line"), [S("start"), x1, y1], [S("end"), x2, y2],
            [S("stroke"), [S("width"), w], [S("type"), S("solid")]], [S("layer"), layer],
            [S("uuid"), str(uuid.uuid4())]]


def rect(x1, y1, x2, y2, layer, w=0.05):
    return [S("fp_rect"), [S("start"), x1, y1], [S("end"), x2, y2],
            [S("stroke"), [S("width"), w], [S("type"), S("solid")]], [S("fill"), S("no")],
            [S("layer"), layer], [S("uuid"), str(uuid.uuid4())]]


def smd(num, x, y, w, h, shape="roundrect", layers=("F.Cu", "F.Mask", "F.Paste"), rr=0.25, paste=True):
    p = [S("pad"), str(num), S("smd"), S(shape), [S("at"), x, y], [S("size"), w, h],
         [S("layers")] + [l for l in layers if paste or l != "F.Paste"]]
    if shape == "roundrect":
        p.append([S("roundrect_rratio"), rr])
    p.append([S("uuid"), str(uuid.uuid4())])
    return p


def footprint(name, desc, items, body, crt, attr="smd"):
    bx, by = body
    cx, cy = crt
    fp = [S("footprint"), name, [S("version"), 20241229], [S("generator"), "fc_gen"],
          [S("generator_version"), "9.0"], [S("layer"), "F.Cu"], [S("descr"), desc],
          fp_text("Reference", "REF**", 0, -cy / 2 - 0.9, "F.SilkS"),
          fp_text("Value", name, 0, cy / 2 + 0.9, "F.Fab"),
          [S("attr"), S(attr)],
          rect(-bx / 2, -by / 2, bx / 2, by / 2, "F.Fab", 0.1),
          rect(-cx / 2, -cy / 2, cx / 2, cy / 2, "F.CrtYd", 0.05)] + items
    fp.append([S("embedded_fonts"), S("no")])
    return fp


def footprints():
    d = os.path.join(OUT, "fc_custom.pretty")
    os.makedirs(d, exist_ok=True)
    fps = {}
    # BMP581: BST-BMP581-DS004-13 section 8.2 / Figure 23 (top view). Pads 0.325 x 0.3 mm + 25 um per
    # side across the row; along the row kept at 0.3 mm so the gap stays >= 0.2 mm as Bosch requires.
    # Top view: pins 3,4,5 left (top->bottom), 6,7 bottom (left->right), 8,9,10 right (bottom->top),
    # 1,2 top (right->left). Row centres 1.525 mm apart, pitch 0.5 mm. No solder mask under the part.
    a = 1.525 / 2
    pads = []
    L, W = 0.375, 0.30
    for i, (n, y) in enumerate([(3, -0.5), (4, 0.0), (5, 0.5)]):
        pads.append(smd(n, -a, y, L, W))
    for n, x in [(6, -0.25), (7, 0.25)]:
        pads.append(smd(n, x, a, W, L))
    for n, y in [(8, 0.5), (9, 0.0), (10, -0.5)]:
        pads.append(smd(n, a, y, L, W))
    for n, x in [(1, 0.25), (2, -0.25)]:
        pads.append(smd(n, x, -a, W, L))
    silk = [line(-1.15, -1.15, -0.6, -1.15, "F.SilkS"), line(-1.15, -1.15, -1.15, -0.95, "F.SilkS"),
            [S("fp_circle"), [S("center"), 1.35, -1.25], [S("end"), 1.45, -1.25],
             [S("stroke"), [S("width"), 0.1], [S("type"), S("solid")]], [S("fill"), S("yes")],
             [S("layer"), "F.SilkS"], [S("uuid"), str(uuid.uuid4())]]]
    fps["Bosch_LGA-10_2x2mm_P0.5mm_BMP581"] = footprint(
        "Bosch_LGA-10_2x2mm_P0.5mm_BMP581",
        "Bosch BMP581 LGA-10 2.0x2.0 mm, land pattern per BST-BMP581-DS004 sec. 8.2; keep vias/traces out from under the part",
        pads + silk, (2.0, 2.0), (2.6, 2.6))
    # TI DRB0008J (VSON-8 3x3), example board layout: pads 0.6 x 0.31, pitch 0.65, rows 2.8 apart,
    # thermal pad 1.65 x 2.4.
    pads = []
    for i in range(4):
        y = -0.975 + 0.65 * i
        pads.append(smd(i + 1, -1.4, y, 0.6, 0.31, rr=0.15))
        pads.append(smd(8 - i, 1.4, y, 0.6, 0.31, rr=0.15))
    pads.append(smd(9, 0, 0, 1.65, 2.4, shape="rect", paste=False))
    for px in (-0.4, 0.4):
        for py in (-0.6, 0.6):
            pads.append([S("pad"), "", S("smd"), S("roundrect"), [S("at"), px, py], [S("size"), 0.6, 0.85],
                         [S("layers"), "F.Paste"], [S("roundrect_rratio"), 0.25], [S("uuid"), str(uuid.uuid4())]])
    silk = [line(-1.5, -1.6, 1.5, -1.6, "F.SilkS"), line(-1.5, 1.6, 1.5, 1.6, "F.SilkS"),
            line(-1.9, -1.6, -1.6, -1.6, "F.SilkS")]
    fps["TI_DRB0008J_VSON-8_3x3mm_P0.65mm"] = footprint(
        "TI_DRB0008J_VSON-8_3x3mm_P0.65mm", "TI DRB0008J VSON-8 3x3 mm, P0.65, EP 1.65x2.4, TI land pattern example",
        pads + silk, (3.0, 3.0), (3.9, 3.5))
    # Battery pads
    pads = [smd(1, -2.5, 0, 3.0, 5.0, shape="rect"), smd(2, 2.5, 0, 3.0, 5.0, shape="rect")]
    silk = [[S("fp_text"), S("user"), "+", [S("at"), -2.5, -3.3, 0], [S("layer"), "F.SilkS"],
             [S("uuid"), str(uuid.uuid4())], [S("effects"), [S("font"), [S("size"), 1, 1], [S("thickness"), 0.15]]]],
            [S("fp_text"), S("user"), "-", [S("at"), 2.5, -3.3, 0], [S("layer"), "F.SilkS"],
             [S("uuid"), str(uuid.uuid4())], [S("effects"), [S("font"), [S("size"), 1, 1], [S("thickness"), 0.15]]]]]
    fps["PowerPads_2x_3x5mm"] = footprint("PowerPads_2x_3x5mm", "Battery lead solder pads, 3x5 mm, 5 mm pitch",
                                          pads + silk, (8.0, 5.0), (8.6, 5.6))
    pads = [smd(1, -1.1, 0, 1.5, 2.0, shape="rect"), smd(2, 1.1, 0, 1.5, 2.0, shape="rect")]
    fps["Pads_2x_1.5x2mm"] = footprint("Pads_2x_1.5x2mm", "Two solder pads 1.5x2 mm (buzzer)", pads,
                                       (3.7, 2.0), (4.2, 2.6))
    # 30.5 mm stack mounting hole for M3 rubber grommet: 4.0 mm NPTH, 6.5 mm keepout
    hole = [S("pad"), "", S("np_thru_hole"), S("circle"), [S("at"), 0, 0], [S("size"), 4.0, 4.0],
            [S("drill"), 4.0], [S("layers"), "*.Cu", "*.Mask"], [S("uuid"), str(uuid.uuid4())]]
    circ = [S("fp_circle"), [S("center"), 0, 0], [S("end"), 3.0, 0],
            [S("stroke"), [S("width"), 0.05], [S("type"), S("solid")]], [S("fill"), S("no")],
            [S("layer"), "F.CrtYd"], [S("uuid"), str(uuid.uuid4())]]
    m = footprint("MountingHole_4.0mm_Grommet", "M3 soft-mount grommet hole, 4.0 mm NPTH, 30.5 mm stack",
                  [hole, circ], (4.0, 4.0), (6.5, 6.5), attr="exclude_from_pos_files exclude_from_bom")
    m = [e for e in m if not (isinstance(e, list) and e and e[0] == "fp_rect" and find1(e, "layer")[1] == "F.CrtYd")]
    fps["MountingHole_4.0mm_Grommet"] = m
    for name, f in fps.items():
        with open(os.path.join(d, name + ".kicad_mod"), "w") as fh:
            fh.write(dump(f) + "\n")
    return fps


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    s = symbols()
    f = footprints()
    print(len(s), "symbols,", len(f), "footprints")
