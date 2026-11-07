"""2D field-solver checks of the fc-h743 stackup with atlc (finite-difference Laplace solver).

Each case is drawn as a cross-section bitmap (2.5 um per pixel) from the stackup written in
kicad/fc.kicad_pcb, then solved by atlc. Colours: red = +1 V conductor, blue = -1 V conductor,
green = ground, other colours = dielectrics passed with -d. Every
cross-section sits in a grounded box: this atlc build gives wrong answers with an open boundary.

Run: python3 xsec.py   (needs atlc on PATH)   -> results.json + one .bmp per case
"""
import json, os, re, subprocess
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PX = 0.005                      # mm per pixel
# stackup (mm) from the board file
T_CU_OUT, T_CU_IN = 0.035, 0.0152
H_PP, ER_PP = 0.1834, 4.021      # 3313+1080 prepreg, F.Cu-In1 and In4-B.Cu
H_CORE, ER_CORE = 0.25, 4.6      # cores, In1-In2 and In3-In4
H_MID, ER_MID = 0.5448, 4.345    # 7628+2116+7628, In2-In3
T_MASK, ER_MASK = 0.015, 3.8     # LPI solder mask over the outer traces (JLC: 10-20 um)
ZONE_CLR = 0.20                  # GND pour clearance on signal layers

COL = {"air": (255, 255, 255), "gnd": (0, 255, 0), "pos": (255, 0, 0), "neg": (0, 0, 255),
       "pp": (0x20, 0x20, 0x20), "core": (0x40, 0x40, 0x40), "mid": (0x60, 0x60, 0x60),
       "mask": (0x80, 0x80, 0x80)}
DIEL = {"pp": ER_PP, "core": ER_CORE, "mid": ER_MID, "mask": ER_MASK}


def n(mm):
    return int(round(mm / PX))


class Canvas:
    def __init__(self, w_mm, h_mm):
        self.W, self.H = n(w_mm), n(h_mm)
        self.a = np.zeros((self.H, self.W, 3), np.uint8)
        self.a[:] = COL["air"]

    def rect(self, x0, y0, x1, y1, what):   # mm, y measured upward from the bottom
        r0, r1 = self.H - n(y1), self.H - n(y0)
        self.a[max(r0, 0):max(r1, 0), max(n(x0), 0):n(x1)] = COL[what]

    def save(self, path):
        # atlc needs a closed boundary: put the cross-section in a grounded box (walls >= 3 h away)
        a = self.a.copy()
        a[0, :] = a[-1, :] = COL["gnd"]; a[:, 0] = a[:, -1] = COL["gnd"]
        Image.fromarray(a, "RGB").save(path)


def microstrip(name, w, gap=None, coplanar=True, width=4.0):
    """F.Cu trace(s) over In1 GND, solder mask on top, optional GND pour beside at ZONE_CLR."""
    h = H_PP + T_CU_OUT + T_MASK + 1.0
    c = Canvas(width, h)
    y = 0.0
    c.rect(0, 0, width, T_CU_IN, "gnd"); y = T_CU_IN
    c.rect(0, y, width, y + H_PP, "pp"); y += H_PP
    yc = y
    xm = width / 2
    if gap is None:
        tr = [(xm - w / 2, xm + w / 2, "pos")]
    else:
        tr = [(xm - gap / 2 - w, xm - gap / 2, "pos"), (xm + gap / 2, xm + gap / 2 + w, "neg")]
    c.rect(0, yc, width, yc + T_CU_OUT + T_MASK, "mask")
    for x0, x1, k in tr:
        c.rect(x0, yc, x1, yc + T_CU_OUT, k)
    if coplanar:
        lo, hi = tr[0][0] - ZONE_CLR, tr[-1][1] + ZONE_CLR
        c.rect(0, yc, lo, yc + T_CU_OUT, "gnd"); c.rect(hi, yc, width, yc + T_CU_OUT, "gnd")
    # side walls at the canvas edge are ground in atlc only if drawn; leave air (wide canvas)
    return c


def stripline_in2(name, w, gap=None, width=3.0, coplanar=True):
    """In2.Cu trace(s): In1 GND 0.25 mm above (core), In3 signal layer then In4 GND below."""
    c = Canvas(width, T_CU_IN * 2 + H_CORE + H_MID + T_CU_IN + H_CORE)
    y = 0.0
    c.rect(0, 0, width, T_CU_IN, "gnd"); y = T_CU_IN                       # In4
    c.rect(0, y, width, y + H_CORE + T_CU_IN, "core"); y += H_CORE + T_CU_IN  # core + In3 (empty)
    c.rect(0, y, width, y + H_MID, "mid"); y += H_MID
    yc = y
    c.rect(0, yc, width, yc + T_CU_IN + H_CORE, "core")
    xm = width / 2
    tr = [(xm - w / 2, xm + w / 2, "pos")] if gap is None else \
         [(xm - gap / 2 - w, xm - gap / 2, "pos"), (xm + gap / 2, xm + gap / 2 + w, "neg")]
    for x0, x1, k in tr:
        c.rect(x0, yc, x1, yc + T_CU_IN, k)
    if coplanar:
        lo, hi = tr[0][0] - ZONE_CLR, tr[-1][1] + ZONE_CLR
        c.rect(0, yc, lo, yc + T_CU_IN, "gnd"); c.rect(hi, yc, width, yc + T_CU_IN, "gnd")
    y = yc + T_CU_IN + H_CORE
    c.rect(0, y, width, y + T_CU_IN, "gnd")                                # In1
    c.a = c.a[: c.H]                                                       # trim
    return c


def broadside_in2_in3(w=0.127, offset=0.0, width=3.0):
    """Worst case for In2/In3 crosstalk: a trace on In2 directly over one on In3."""
    c = Canvas(width, T_CU_IN * 4 + H_CORE * 2 + H_MID)
    y = 0.0
    c.rect(0, 0, width, T_CU_IN, "gnd"); y = T_CU_IN                       # In4
    c.rect(0, y, width, y + H_CORE, "core"); y += H_CORE
    xm = width / 2
    c.rect(0, y, width, y + T_CU_IN + H_MID, "mid")
    c.rect(xm - w / 2 + offset, y, xm + w / 2 + offset, y + T_CU_IN, "neg")  # In3 trace
    y += T_CU_IN + H_MID
    c.rect(0, y, width, y + T_CU_IN + H_CORE, "core")
    c.rect(xm - w / 2, y, xm + w / 2, y + T_CU_IN, "pos")                    # In2 trace
    y += T_CU_IN + H_CORE
    c.rect(0, y, width, y + T_CU_IN, "gnd")                                  # In1
    return c


def run(name, canvas):
    bmp = os.path.join(HERE, f"{name}.bmp")
    canvas.save(bmp)
    args = ["atlc", "-S", "-s"]
    for k, er in DIEL.items():
        args += ["-d", "%02x%02x%02x=%g" % (*COL[k], er)]
    out = subprocess.run(args + [bmp], capture_output=True, text=True, cwd=HERE).stdout
    vals = dict(re.findall(r"(Er|Zo|Zodd|Zeven|Zdiff|Zcomm|Er_odd|Er_even|C|L|Codd|Ceven)\s*=\s*([-\d.eE+]+)", out))
    print(name, out.strip().splitlines()[-1] if out.strip() else "(no output)")
    return {k: float(v) for k, v in vals.items()}, out


CASES = {
    "usb_pair_F_0.25_0.15_coplanar": microstrip("usb", 0.25, 0.15, True),
    "usb_pair_F_0.25_0.15_open": microstrip("usb", 0.25, 0.15, False),
    "sig_F_0.127_open": microstrip("sig", 0.127, None, False),
    "sig_F_0.127_coplanar": microstrip("sig", 0.127, None, True),
    "sig_In2_0.127": stripline_in2("s2", 0.127, None, coplanar=False),
    "sig_In2_0.127_coplanar": stripline_in2("s2", 0.127, None, coplanar=True),
    "broadside_In2_In3_0.127": broadside_in2_in3(),
    "edge_In2_0.127_gap_0.10": stripline_in2("e2", 0.127, 0.10, coplanar=False),
    "edge_F_0.127_gap_0.10": microstrip("e1", 0.127, 0.10, False),
}

if __name__ == "__main__":
    res = {}
    for name, cv in CASES.items():
        v, raw = run(name, cv)
        if "Zodd" in v and "Zeven" in v:
            ze, zo = v["Zeven"], v["Zodd"]
            v["K"] = (ze - zo) / (ze + zo)          # coupling coefficient
            v["NEXT_sat"] = v["K"] / 2              # saturated backward (near-end) crosstalk, homogeneous approx
        res[name] = v
    json.dump(res, open(os.path.join(HERE, "results.json"), "w"), indent=1)
    for k, v in res.items():
        print(k, {a: round(b, 3) for a, b in v.items() if a in ("Zo", "Zodd", "Zeven", "Zdiff", "Er", "K", "NEXT_sat")})
