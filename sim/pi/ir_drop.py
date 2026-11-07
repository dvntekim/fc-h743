"""DC voltage drop on the power nets of fc-h743, from the routed copper.

Method (a 2.5D resistive-mesh solver, the same idea as commercial PDN DC tools):
  * every copper layer of one net is rasterised at 50 um from out/geom.json
    (tracks, filled zones, pads) exported by export_geom.py;
  * neighbouring copper cells on a layer are joined by the sheet resistance rho/t;
  * vias and plated pad holes join the layers with their barrel resistance;
  * source pads are held at 0 V, sink pads draw their current spread over the pad area;
  * the sparse system is solved with scipy; the result is the drop at every sink.
Copper: rho = 1.72e-8 Ohm m at 20 C (x1.10 at 45 C), outer 35 um, inner 15.2 um, via plating 18 um.

Run: python3 ir_drop.py ../../out/geom.json  -> results.json + one PNG per net
"""
import json, math, os, sys
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from PIL import Image, ImageDraw
from shapely.geometry import LineString, Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "../../out/geom.json")))
RES = 0.05                       # mm per cell
X0, Y0, W = 75.0, 75.0, 50.0
N = int(W / RES)
RHO = 1.72e-8 * 1.10             # Ohm m at ~45 C
T = {"F": 35e-6, "B": 35e-6, "In1": 15.2e-6, "In2": 15.2e-6, "In3": 15.2e-6, "In4": 15.2e-6}
ORDER = ["F", "In1", "In2", "In3", "In4", "B"]
Z = {"F": 0.0, "In1": 0.2184, "In2": 0.4836, "In3": 1.0436, "In4": 1.3088, "B": 1.565}  # mm, centre of each copper
PLATE = 18e-6


def px(x, y):
    return ((x - X0) / RES, (y - Y0) / RES)


def raster(net):
    imgs = {l: Image.new("1", (N, N), 0) for l in ORDER}
    dr = {l: ImageDraw.Draw(imgs[l]) for l in ORDER}
    for t in G["tracks"]:
        if t["net"] != net:
            continue
        s = LineString([(t["x1"], t["y1"]), (t["x2"], t["y2"])]).buffer(t["w"] / 2, 8)
        dr[t["l"]].polygon([px(*p) for p in s.exterior.coords], fill=1)
    for z in G["zones"] + G["pads"]:
        if z["net"] != net:
            continue
        for outline, holes in z["polys"]:
            if len(outline) >= 3:
                dr[z["l"]].polygon([px(*p) for p in outline], fill=1)
            for h in holes:
                if len(h) >= 3:
                    dr[z["l"]].polygon([px(*p) for p in h], fill=0)
    return {l: np.array(imgs[l], dtype=bool) for l in ORDER}


def pad_cells(cu, ref, padnum, layer=None):
    """cells (layer, iy, ix) of a pad, from its polygon"""
    cells = []
    for p in G["pads"]:
        if p["ref"] == ref and p["pad"] == padnum and (layer is None or p["l"] == layer):
            im = Image.new("1", (N, N), 0); d = ImageDraw.Draw(im)
            for outline, holes in p["polys"]:
                d.polygon([px(*q) for q in outline], fill=1)
            m = np.array(im, dtype=bool) & cu[p["l"]]
            ys, xs = np.nonzero(m)
            cells += [(p["l"], y, x) for y, x in zip(ys, xs)]
    return cells


def solve(net, sources, sinks):
    """sources: [(ref, pad)], sinks: [(ref, pad, amps)] -> dict of results"""
    cu = raster(net)
    idx = {}
    k = 0
    for l in ORDER:
        ys, xs = np.nonzero(cu[l])
        for y, x in zip(ys, xs):
            idx[(l, y, x)] = k; k += 1
    rows, cols, vals = [], [], []

    def add(a, b, g):
        rows.extend([a, b, a, b]); cols.extend([a, b, b, a]); vals.extend([g, g, -g, -g])

    for l in ORDER:
        g = T[l] / RHO                       # 1 / sheet resistance (square cells)
        m = cu[l]
        for dy, dx in ((0, 1), (1, 0)):
            both = m[: N - dy, : N - dx] & m[dy:, dx:]
            ys, xs = np.nonzero(both)
            for y, x in zip(ys, xs):
                add(idx[(l, y, x)], idx[(l, y + dy, x + dx)], g)
    # vias and plated holes: barrel between consecutive layers that carry this net's copper there
    holes = [(v["x"], v["y"], v["drill"]) for v in G["vias"] if v["net"] == net]
    seen = set()
    for p in G["pads"]:
        if p["net"] == net and p["drill"] > 0 and (p["ref"], p["pad"], p["x"], p["y"]) not in seen:
            seen.add((p["ref"], p["pad"], p["x"], p["y"])); holes.append((p["x"], p["y"], p["drill"]))
    nvias = 0
    for x, y, d in holes:
        ix, iy = int((x - X0) / RES), int((y - Y0) / RES)
        ls = [l for l in ORDER if cu[l][iy, ix]]
        for a, b in zip(ls, ls[1:]):
            L = (Z[b] - Z[a]) * 1e-3
            R = RHO * L / (math.pi * (d * 1e-3 + PLATE) * PLATE)
            add(idx[(a, iy, ix)], idx[(b, iy, ix)], 1 / R)
        nvias += 1
    A = sp.csr_matrix((vals, (rows, cols)), shape=(k, k))
    rhs = np.zeros(k)
    src = set()
    for ref, pad in sources:
        for c in pad_cells(cu, ref, pad):
            src.add(idx[c])
    sink_cells = {}
    for ref, pad, amps in sinks:
        cs = [idx[c] for c in pad_cells(cu, ref, pad)]
        if not cs:
            raise SystemExit(f"{net}: sink {ref}.{pad} has no copper")
        sink_cells[(ref, pad)] = cs
        for c in cs:
            rhs[c] -= amps / len(cs)
    # Dirichlet at sources: V = 0
    keep = np.array([i for i in range(k) if i not in src])
    Ak = A[keep][:, keep]
    v = np.zeros(k)
    # only solve the part connected to the sources (floating islands are left at 0 and flagged)
    v[keep] = spla.spsolve(Ak.tocsc(), rhs[keep])
    res = {"net": net, "cells": k, "barrels": nvias, "sinks": {}}
    for (ref, pad), cs in sink_cells.items():
        res["sinks"][f"{ref}.{pad}"] = {"drop_mV": round(-1000 * float(np.mean(v[cs])), 2),
                                        "worst_mV": round(-1000 * float(np.min(v[cs])), 2)}
    # power lost in copper
    res["copper_loss_mW"] = round(1000 * float(v @ (A @ v)), 1)
    # current density hot spot on each layer (A/mm of width ~ |grad V| * t / rho)
    jmax = {}
    for l in ORDER:
        m = cu[l]
        if not m.any():
            continue
        V = np.full((N, N), np.nan)
        for (ll, y, x), i in idx.items():
            if ll == l:
                V[y, x] = v[i]
        gx = np.abs(np.diff(V, axis=1)) / (RES * 1e-3)
        gy = np.abs(np.diff(V, axis=0)) / (RES * 1e-3)
        J = np.nanmax([np.nanmax(gx) if np.isfinite(gx).any() else 0, np.nanmax(gy) if np.isfinite(gy).any() else 0]) / RHO
        jmax[l] = round(J * 1e-6, 1)        # A/mm^2
        if l in ("F", "In2", "B"):
            import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(5, 5))
            im = ax.imshow(-1000 * V, extent=[X0, X0 + W, Y0 + W, Y0], cmap="viridis")
            ax.set_title(f"{net} on {l}: drop (mV)"); fig.colorbar(im, ax=ax, shrink=0.8)
            fig.savefig(os.path.join(HERE, f"{net.replace('+', 'P')}_{l}.png"), dpi=110, bbox_inches="tight"); plt.close(fig)
    res["max_current_density_A_per_mm2"] = jmax
    return res


CASES = [
    # battery entry: pads -> FET drain. 3 A = 2S at 6 V feeding a 15 W buck load (worst case)
    ("VBAT_RAW", [("J1", "1")], [("Q1", "5", 3.0)]),
    ("VBAT", [("Q1", "1"), ("Q1", "2"), ("Q1", "3")], [("U1", "2", 3.0)]),
    # 5 V: inductor -> loads at their current limits (LM66100 main path, two TPS2553, heater)
    # rev B heater: 2 x 12 R in series on the IMU island, 5.09 V / 24 R = 0.21 A into R44 pin 1
    ("+5V", [("L1", "2")], [("U2", "1", 0.5), ("U6", "1", 1.3), ("U7", "1", 1.2), ("R44", "1", 0.212)]),
    # 3V3: inductor -> MCU VDD pins (50 mA each), microSD (100 mA), CAN VIO, LEDs
    ("+3V3", [("L2", "2")], [("U10", p, 0.05) for p in ("11", "27", "50", "75", "100")] +
     [("J21", "4", 0.10), ("U40", "5", 0.005), ("U41", "5", 0.005)]),
]

if __name__ == "__main__":
    out = []
    for net, src, snk in CASES:
        r = solve(net, src, snk)
        print(json.dumps(r))
        out.append(r)
    json.dump(out, open(os.path.join(HERE, "results.json"), "w"), indent=1)
