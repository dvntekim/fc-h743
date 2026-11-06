"""Steady-state board temperature of fc-h743 in still air (conservative: no prop wash).

Model: the 1.6 mm board as one conducting sheet on a 0.25 mm grid. In-plane conductance of each
cell = sum over the six copper layers of k_cu * t * (copper fill of that cell, from the routed
board) + k_FR4 * board thickness. Both faces lose heat by natural convection + radiation
(h per face). Heat sources are spread over each part's pads. The through-thickness gradient is
ignored (dielectrics are 0.18-0.54 mm and GND vias are dense), which is the usual first-order
board model. Part case temperature = local board temperature + P x psi_JB (datasheet or typical).

Run: python3 thermal.py ../../out/geom.json  -> results.json, map_<case>.png
"""
import json, os, sys
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from PIL import Image, ImageDraw
from shapely.geometry import LineString

HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "../../out/geom.json")))
X0, Y0, W = 75.0, 75.0, 50.0
FINE, CELL = 0.05, 0.25
NF, N = int(W / FINE), int(W / CELL)
K_CU, K_FR4 = 390.0, 0.8          # W/mK (FR4 in-plane)
T_CU = {"F": 35e-6, "B": 35e-6, "In1": 15.2e-6, "In2": 15.2e-6, "In3": 15.2e-6, "In4": 15.2e-6}
T_BOARD = 1.6e-3
H_FACE = float(os.environ.get("H_FACE", "12"))   # W/m2K per face: natural convection ~7 + radiation ~5
T_AMB = float(os.environ.get("T_AMB", "25"))

# psi_JB (junction to board), C/W: datasheet values where published, otherwise typical for the package
PSI = {"U1": 19.0, "D3": 25.0, "L1": 15.0, "U10": 8.0, "U4": 40.0, "U6": 50.0, "U7": 50.0, "Q1": 10.0,
       "R44": 30.0, "R45": 30.0, "R46": 30.0, "R47": 30.0}


def fill_fraction():
    frac = np.zeros((N, N))
    s = int(CELL / FINE)
    for l in T_CU:
        im = Image.new("1", (NF, NF), 0); d = ImageDraw.Draw(im)
        P = lambda p: ((p[0] - X0) / FINE, (p[1] - Y0) / FINE)
        for t in G["tracks"]:
            if t["l"] == l:
                g = LineString([(t["x1"], t["y1"]), (t["x2"], t["y2"])]).buffer(t["w"] / 2, 4)
                d.polygon([P(p) for p in g.exterior.coords], fill=1)
        for z in G["zones"] + G["pads"]:
            if z["l"] == l:
                for o, holes in z["polys"]:
                    if len(o) >= 3:
                        d.polygon([P(p) for p in o], fill=1)
                    for h in holes:
                        if len(h) >= 3:
                            d.polygon([P(p) for p in h], fill=0)
        a = np.array(im, dtype=float).reshape(N, s, N, s).mean(axis=(1, 3))
        frac += a * T_CU[l] * K_CU
    return frac + K_FR4 * T_BOARD      # W/K per square (sheet conductance)


def part_mask(ref):
    m = np.zeros((N, N))
    for p in G["pads"]:
        if p["ref"] == ref:
            xs = [q[0] for o, h in p["polys"] for q in o]; ys = [q[1] for o, h in p["polys"] for q in o]
            i0, i1 = int((min(ys) - Y0) / CELL), int((max(ys) - Y0) / CELL) + 1
            j0, j1 = int((min(xs) - X0) / CELL), int((max(xs) - X0) / CELL) + 1
            m[i0:i1, j0:j1] = 1
    return m / m.sum()


def solve(sources):
    K = fill_fraction()
    idx = np.arange(N * N).reshape(N, N)
    rows, cols, vals = [], [], []
    for dy, dx in ((0, 1), (1, 0)):
        a = idx[: N - dy, : N - dx].ravel(); b = idx[dy:, dx:].ravel()
        g = 2 / (1 / K[: N - dy, : N - dx].ravel() + 1 / K[dy:, dx:].ravel())   # harmonic mean
        rows += [a, b, a, b]; cols += [a, b, b, a]; vals += [g, g, -g, -g]
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(N * N, N * N))
    A = A + sp.diags(np.full(N * N, 2 * H_FACE * (CELL * 1e-3) ** 2))
    q = np.zeros((N, N))
    for ref, pw in sources.items():
        q += pw * part_mask(ref)
    T = spla.spsolve(A.tocsc(), q.ravel()).reshape(N, N) + T_AMB
    return T, K


def report(name, sources):
    T, K = solve(sources)
    out = {"case": name, "h_face": H_FACE, "t_amb": T_AMB, "total_W": round(sum(sources.values()), 2),
           "board_max_C": round(float(T.max()), 1), "board_mean_C": round(float(T.mean()), 1), "parts": {}}
    for ref, pw in sources.items():
        m = part_mask(ref) > 0
        tb = float(T[m].max())
        out["parts"][ref] = {"W": pw, "board_C": round(tb, 1), "case_est_C": round(tb + pw * PSI.get(ref, 20), 1)}
    for ref in ("U20", "U21", "U22", "Y1"):
        m = part_mask(ref) > 0
        out["parts"][ref] = {"W": 0, "board_C": round(float(T[m].max()), 1)}
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(5.5, 5))
    im = ax.imshow(T, extent=[X0, X0 + W, Y0 + W, Y0], cmap="inferno")
    for f in G["fps"]:
        if f["ref"] in sources or f["ref"] in ("U20", "U21", "U22"):
            ax.text(f["x"], f["y"], f["ref"], color="cyan", fontsize=6, ha="center")
    ax.set_title(f"{name}: {out['total_W']} W, still air, {T_AMB:.0f} C ambient")
    fig.colorbar(im, ax=ax, shrink=0.8, label="C")
    fig.savefig(os.path.join(HERE, f"map_{name}.png"), dpi=120, bbox_inches="tight"); plt.close(fig)
    return out


# Loss estimates (W). Buck: TI equations (conduction I^2*Rdson*D + switching Vin*Iout*fsw*tr),
# diode (1-D)*Iout*Vf, inductor I^2*DCR; MCU at 480 MHz typical; heater 4 x 5.09^2/120 when on.
BASE_6S = {"U1": 0.30, "D3": 1.10, "L1": 0.38, "U10": 0.70, "U4": 0.13, "U6": 0.10, "U7": 0.06, "Q1": 0.01}
BASE_4S = {"U1": 0.12, "D3": 0.45, "L1": 0.09, "U10": 0.70, "U4": 0.13, "U6": 0.03, "U7": 0.01, "Q1": 0.002}
HEATER = {r: 0.2158 for r in ("R44", "R45", "R46", "R47")}
CASES = {"6S_2.5A": BASE_6S, "4S_1.2A": BASE_4S, "4S_1.2A+heater": {**BASE_4S, **HEATER}}
H_CASES = {12: "still air (bench)", 50: "prop wash (in flight)"}

if __name__ == "__main__":
    res = []
    for h in H_CASES:
        H_FACE = h
        for k, v in CASES.items():
            r = report(f"{k}_h{h}", v); res.append(r)
            imu = max(r["parts"]["U20"]["board_C"], r["parts"]["U21"]["board_C"])
            print(f"h={h:3d} {k:16s} {r['total_W']:.2f} W  board max {r['board_max_C']}  IMU {imu}  D3 case {r['parts']['D3']['case_est_C']}")
    json.dump(res, open(os.path.join(HERE, "results.json"), "w"), indent=1)
