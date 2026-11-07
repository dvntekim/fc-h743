"""Crosstalk scan of the routed board: every clock / fast-edge net against its neighbours.

For each aggressor segment, find victim segments of other nets on the same layer that run
parallel (within 10 deg) with an edge gap below 0.5 mm, and broadside segments on the facing
inner layer (In2 <-> In3). The coupled length is summed per victim net. Backward (near-end)
crosstalk is estimated with the standard saturating model
    NEXT = (K / 2) * min(1, L / L_sat),  L_sat = t_rise * v / 2,
with K(gap) from the atlc sweep (k_sweep.json) and K = 0.12 for broadside In2/In3.
Run: python3 xtalk_scan.py ../../out/geom.json
"""
import json, math, os, sys, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(sys.argv[1]))
KS = json.load(open(os.path.join(HERE, "k_sweep.json")))
K_BROAD = json.load(open(os.path.join(HERE, "results.json")))["broadside_In2_In3_0.127"]
K_BROAD = (K_BROAD["Zeven"] - K_BROAD["Zodd"]) / (K_BROAD["Zeven"] + K_BROAD["Zodd"])
AGG = {  # net: rise time (s), from driver speed setting and series R
    "SD_CLK": 2e-9, "SPI1_SCK": 2e-9, "SPI2_SCK": 2e-9, "IMU_CLKIN": 5e-9,
    "HSE_IN": 3e-9, "HSE_OUT": 3e-9, "CAN1_TX": 5e-9, "CAN2_TX": 5e-9,
    "M1": 3e-9, "M2": 3e-9, "M3": 3e-9, "M4": 3e-9,
}
V = {"F": 1.7e8, "B": 1.7e8, "In2": 1.41e8, "In3": 1.41e8}


def k_of(layer, gap):
    lay = "F" if layer in ("F", "B") else "In2"
    pts = sorted((float(k.split(":")[1]), v) for k, v in KS.items() if k.startswith(lay + ":"))
    gs, ks = zip(*pts)
    return float(np.interp(gap, gs, ks, right=0.0))


def seg(t):
    return np.array([t["x1"], t["y1"]]), np.array([t["x2"], t["y2"]])


def overlap(a, b):
    """parallel overlap length and centre-line distance of two segments (or None)"""
    a0, a1 = seg(a); b0, b1 = seg(b)
    da = a1 - a0; la = np.linalg.norm(da)
    db = b1 - b0; lb = np.linalg.norm(db)
    if la < 0.05 or lb < 0.05:
        return None
    ua, ub = da / la, db / lb
    if abs(np.dot(ua, ub)) < math.cos(math.radians(10)):
        return None
    # project b onto a's axis
    s0, s1 = sorted((np.dot(b0 - a0, ua), np.dot(b1 - a0, ua)))
    lo, hi = max(0, s0), min(la, s1)
    if hi - lo <= 0:
        return None
    mid = a0 + ua * (lo + hi) / 2
    n = np.array([-ua[1], ua[0]])
    d = abs(np.dot((b0 + b1) / 2 - mid, n))
    return hi - lo, d


tracks = [t for t in G["tracks"] if t["net"] and t["net"] != "GND"]
by_layer = collections.defaultdict(list)
for t in tracks:
    by_layer[t["l"]].append(t)
rows = []
for agg, tr in AGG.items():
    acc = collections.defaultdict(lambda: [0.0, 1.0, 0.0])   # victim -> [length, min gap, NEXT]
    for a in (t for t in tracks if t["net"] == agg):
        cands = [(b, b["l"]) for b in by_layer[a["l"]] if b["net"] != agg]
        facing = {"In2": "In3", "In3": "In2"}.get(a["l"])
        if facing:
            cands += [(b, "broad") for b in by_layer[facing] if b["net"] != agg]
        for b, kind in cands:
            o = overlap(a, b)
            if not o:
                continue
            L, d = o
            if kind == "broad":
                if d > (a["w"] + b["w"]) / 2:
                    continue
                k = K_BROAD
            else:
                gap = d - (a["w"] + b["w"]) / 2
                if gap > 0.5:
                    continue
                k = k_of(a["l"], gap)
                acc[b["net"]][1] = min(acc[b["net"]][1], gap)
            lsat = tr * V[a["l"]] / 2 * 1e3
            acc[b["net"]][0] += L
            acc[b["net"]][2] += (k / 2) * min(1, L / lsat)
    for victim, (L, g, nx) in acc.items():
        rows.append((agg, victim, round(L, 1), round(g, 3) if g < 1 else None, round(100 * min(nx, 0.5), 2)))
rows.sort(key=lambda r: -r[4])
json.dump(rows, open(os.path.join(HERE, "xtalk.json"), "w"), indent=1)
print("aggressor, victim, coupled mm, min gap mm, NEXT % of aggressor swing")
for r in rows[:25]:
    print(r)
