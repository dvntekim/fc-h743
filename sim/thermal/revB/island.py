"""Rev B: can a thermally isolated IMU island let the heater hold a set point?

Extends thermal.py (same board model: 0.25 mm sheet from the routed copper, convection + radiation
on both faces) with:
  * an island around the IMUs, bounded by either
      - a "moat": a ring where all copper pours and planes are removed on every layer (tracks
        that cross it stay; FR4 stays), or
      - a "slot": a routed cut-out through the board (nothing conducts) except at bridges,
    with bridges ("necks") that keep GND and routing continuous;
  * the MCU as its own node: 0.70 W in the die, coupled to the board through its 100 leads
    (~0.5 W/K to the pad ring) and through the ~0.1 mm air gap under the 14 x 14 mm body
    (k_air * A / gap ~ 0.05 W/K) to the copper underneath, which is the island;
  * the heater (4 resistors) moved onto the island.

For each design it reports the IMU temperature with the heater off and full on in a hot case
(35 C ambient, still air, 6S / 2.5 A) and a cold case (15 C ambient, prop wash, 4S / 1.2 A).
A set point is holdable when it is above every heater-off temperature and below every
heater-full temperature; the width of that window is the figure of merit.

Run: python3 island.py ../../out/geom.json -> island_results.json, island_<design>.png
"""
import json, os, sys, itertools
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from PIL import Image, ImageDraw
from shapely.geometry import LineString, box, Point

HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "../../out/geom.json")))
X0, Y0, W = 75.0, 75.0, 50.0
FINE, CELL = 0.05, 0.25
NF, N = int(W / FINE), int(W / CELL)
K_CU, K_FR4, K_AIR = 390.0, 0.8, 0.026
T_CU = {"F": 35e-6, "B": 35e-6, "In1": 15.2e-6, "In2": 15.2e-6, "In3": 15.2e-6, "In4": 15.2e-6}
T_BOARD = 1.6e-3
CX, CY = 100.0, 100.0               # MCU / IMU centre
BODY = 7.0                          # LQFP-100 body half-size, mm
G_LEADS = 0.5                       # W/K, 100 gull-wing leads in parallel
GAP = 0.1e-3                        # m, body-to-board air gap
P_MCU = 0.70
HEATER_W = 4 * 5.09 ** 2 / 120      # 0.86 W at the 5.09 V rail
IMU_REFS = ("U20", "U21")
HEATER_REFS = ("R44", "R45", "R46", "R47")
HEATER_AT_REV_B = {"R44": (100.0, 96.6), "R45": (100.0, 103.4), "R46": (94.6, 100.0), "R47": (105.4, 100.0)}

BASE_6S = {"U1": 0.30, "D3": 1.10, "L1": 0.38, "U4": 0.13, "U6": 0.10, "U7": 0.06, "Q1": 0.01}
BASE_4S = {"U1": 0.12, "D3": 0.45, "L1": 0.09, "U4": 0.13, "U6": 0.03, "U7": 0.01, "Q1": 0.002}
CASES = {"hot: 35C, still air, 6S 2.5A": (35.0, 12.0, BASE_6S),
         "cold: 15C, prop wash, 4S 1.2A": (15.0, 50.0, BASE_4S)}
# operating envelope used for the requirement: flight at 15-35 C plus a 25 C bench warm-up
ENVELOPE = {"bench: 25C, still air, 4S 1.2A": (25.0, 12.0, BASE_4S),
            "flight cold: 15C, prop wash, 4S 1.2A": (15.0, 50.0, BASE_4S),
            "flight hot: 35C, prop wash, 6S 2.5A": (35.0, 50.0, BASE_6S)}


def P(p):
    return ((p[0] - X0) / FINE, (p[1] - Y0) / FINE)


def layer_raster(l, kinds):
    im = Image.new("1", (NF, NF), 0); d = ImageDraw.Draw(im)
    if "tracks" in kinds:
        for t in G["tracks"]:
            if t["l"] == l:
                g = LineString([(t["x1"], t["y1"]), (t["x2"], t["y2"])]).buffer(t["w"] / 2, 4)
                d.polygon([P(p) for p in g.exterior.coords], fill=1)
    for key in kinds - {"tracks"}:
        for z in G[key]:
            if z["l"] == l:
                for o, holes in z["polys"]:
                    if len(o) >= 3:
                        d.polygon([P(p) for p in o], fill=1)
                    for h in holes:
                        if len(h) >= 3:
                            d.polygon([P(p) for p in h], fill=0)
    return np.array(im, dtype=bool)


_CACHE = {}


def rasters():
    if not _CACHE:
        for l in T_CU:
            _CACHE[l] = (layer_raster(l, {"tracks", "pads"}), layer_raster(l, {"zones"}))
    return _CACHE


def ring_mask(half_x, half_y, width, necks, cx=CX, cy=CY):
    """fine-grid mask of the boundary ring minus the necks; necks = [(x, y, w)] gaps in the ring"""
    im = Image.new("1", (NF, NF), 0); d = ImageDraw.Draw(im)
    outer = box(cx - half_x - width, cy - half_y - width, cx + half_x + width, cy + half_y + width)
    inner = box(cx - half_x, cy - half_y, cx + half_x, cy + half_y)
    ring = outer.difference(inner)
    for nx, ny, nw in necks:
        ring = ring.difference(Point(nx, ny).buffer(nw / 2, cap_style=3))
    geoms = getattr(ring, "geoms", [ring])
    for g in geoms:
        d.polygon([P(p) for p in g.exterior.coords], fill=1)
        for h in g.interiors:
            d.polygon([P(p) for p in h.coords], fill=0)
    return np.array(im, dtype=bool)


def sheet(design):
    """sheet conductance per cell (W/K per square) and a mask of cells that are cut away"""
    s = int(CELL / FINE)
    K = np.zeros((N, N))
    cut = np.zeros((N, N), bool)
    ring = ring_mask(*design["ring"], *(design.get("center") or (CX, CY))) if design.get("ring") else np.zeros((NF, NF), bool)
    for l, (keep, zones) in rasters().items():
        cu = keep | zones
        if design.get("kind") == "moat":
            cu = keep | (zones & ~ring)            # pours and planes stop at the moat; tracks cross it
        elif design.get("kind") == "slot":
            cu = cu & ~ring
        K += cu.reshape(N, s, N, s).mean(axis=(1, 3)) * T_CU[l] * K_CU
    fr4 = np.ones((N, N)) * K_FR4 * T_BOARD
    if design.get("kind") == "slot":
        frac_cut = ring.reshape(N, s, N, s).mean(axis=(1, 3))
        fr4 *= (1 - frac_cut)
        cut = frac_cut > 0.99
    return K + fr4 + 1e-9, cut


def rect_mask(x0, y0, x1, y1):
    m = np.zeros((N, N))
    m[int((y0 - Y0) / CELL):int((y1 - Y0) / CELL) + 1, int((x0 - X0) / CELL):int((x1 - X0) / CELL) + 1] = 1
    return m


def pad_mask(ref):
    m = np.zeros((N, N))
    for p in G["pads"]:
        if p["ref"] == ref:
            xs = [q[0] for o, h in p["polys"] for q in o]; ys = [q[1] for o, h in p["polys"] for q in o]
            m += rect_mask(min(xs), min(ys), max(xs), max(ys))
    return (m > 0).astype(float)


def solve(design, amb, h, sources, heater_w):
    K, cut = sheet(design)
    n = N * N
    idx = np.arange(n).reshape(N, N)
    rows, cols, vals = [], [], []
    for dy, dx in ((0, 1), (1, 0)):
        a = idx[: N - dy, : N - dx].ravel(); b = idx[dy:, dx:].ravel()
        g = 2 / (1 / K[: N - dy, : N - dx].ravel() + 1 / K[dy:, dx:].ravel())
        rows += [a, b, a, b]; cols += [a, b, b, a]; vals += [g, g, -g, -g]
    area = (CELL * 1e-3) ** 2
    conv = np.where(cut.ravel(), 0.0, 2 * h * area)
    # MCU node (index n): leads to the pad ring, air gap to the copper under the body, top to air
    m = n
    ring_cells = pad_mask("U10").ravel()
    body = rect_mask(CX - BODY, CY - BODY, CX + BODY, CY + BODY).ravel() * (1 - cut.ravel())
    g_lead = G_LEADS * ring_cells / ring_cells.sum()
    g_air = K_AIR * area / GAP * body
    for gv in (g_lead, g_air):
        nz = np.nonzero(gv)[0]
        rows += [nz, np.full(nz.size, m), nz, np.full(nz.size, m)]
        cols += [nz, np.full(nz.size, m), np.full(nz.size, m), nz]
        vals += [gv[nz], gv[nz], -gv[nz], -gv[nz]]
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n + 1, n + 1))
    diag = np.concatenate([conv, [h * (2 * BODY * 1e-3) ** 2]])
    A = A + sp.diags(diag)
    q = np.zeros(n + 1)
    for ref, pw in sources.items():
        pm = pad_mask(ref).ravel(); q[:n] += pw * pm / pm.sum()
    q[m] += P_MCU
    if heater_w > 0 and design.get("center"):
        cx, cy = design["center"]; hx, hy = design["ring"][0], design["ring"][1]
        hm = (rect_mask(cx - hx + 0.3, cy - hy + 0.3, cx + hx - 0.3, cy + hy - 0.3) - rect_mask(cx - hx + 1.6, cy - hy + 1.6, cx + hx - 1.6, cy + hy - 1.6)).ravel()
        q[:n] += heater_w * hm / hm.sum()          # heater ring just inside the island edge
    elif heater_w > 0:
        for ref in HEATER_REFS:
            if design.get("heater_moved"):
                x, y = HEATER_AT_REV_B[ref]
                hm = rect_mask(x - 0.8, y - 0.8, x + 0.8, y + 0.8).ravel()
            else:
                hm = pad_mask(ref).ravel()
            q[:n] += heater_w / 4 * hm / hm.sum()
    T = spla.spsolve(A.tocsc(), q) + amb
    if design.get("center"):
        cx, cy = design["center"]
        imu = float(T[:n][rect_mask(cx - 2.5, cy - 1.5, cx + 2.5, cy + 1.5).ravel() > 0].mean())
    else:
        imu = max(float(T[:n][pad_mask(r).ravel() > 0].mean()) for r in IMU_REFS)
    return imu, float(T[m]), T[:n].reshape(N, N)


def evaluate(name, design, heater_w=HEATER_W, plot=False):
    out = {"design": name, **{k: v for k, v in design.items() if k != "ring"}, "ring": design.get("ring"),
           "heater_W": round(heater_w, 2), "cases": {}}
    offs, fulls = [], []
    for cname, (amb, h, src) in CASES.items():
        t_off, _, _ = solve(design, amb, h, src, 0.0)
        t_full, mcu, T = solve(design, amb, h, src, heater_w)
        out["cases"][cname] = {"imu_heater_off_C": round(t_off, 1), "imu_heater_full_C": round(t_full, 1),
                               "heater_lift_C": round(t_full - t_off, 1), "mcu_C": round(mcu, 1)}
        offs.append(t_off); fulls.append(t_full)
        if plot:
            import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(5, 4.6))
            im = ax.imshow(T, extent=[X0, X0 + W, Y0 + W, Y0], cmap="inferno")
            ax.set_xlim(85, 115); ax.set_ylim(115, 85)
            ax.set_title(f"{name}\n{cname}, heater full", fontsize=8); fig.colorbar(im, ax=ax, shrink=0.8, label="C")
            fig.savefig(os.path.join(HERE, f"island_{name}_{'hot' if 'hot' in cname else 'cold'}.png"), dpi=110, bbox_inches="tight")
            plt.close(fig)
    lo, hi = max(offs), min(fulls)
    out["holdable_window_C"] = [round(lo, 1), round(hi, 1)]
    out["window_width_C"] = round(hi - lo, 1)
    return out


def necks_for(hx, hy, w, nw):
    """two bridges, top and bottom centre, where the IMU nets and GND enter (the MCU's SPI pins
    are on its left/top edges; the exact positions are set in layout)"""
    return [(CX, CY - hy - w / 2, nw), (CX, CY + hy + w / 2, nw)]


if __name__ == "__main__":
    results = [evaluate("revA", {"kind": None}, plot=True)]
    print(json.dumps(results[-1]))
    for kind, (hx, hy), w, nw in itertools.product(("moat", "slot"), ((5.6, 4.6), (6.0, 5.0)), (0.6, 1.0), (1.0, 2.0)):
        if hx + w > 6.9:        # stay inside the MCU's pad ring (inner pad edge at 6.95 mm)
            continue
        name = f"{kind}_{2*hx:.0f}x{2*hy:.0f}_w{w}_neck{nw}"
        d = {"kind": kind, "ring": (hx, hy, w, necks_for(hx, hy, w, nw)), "heater_moved": True}
        r = evaluate(name, d)
        results.append(r)
        print(name, r["cases"], "window", r["holdable_window_C"], "width", r["window_width_C"], flush=True)
    json.dump(results, open(os.path.join(HERE, "island_results.json"), "w"), indent=1)
