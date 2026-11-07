"""Rev B island on the routed copper: the same solver as island.py, but the board, the slots,
the heater resistors and the IMU pads all come from the routed rev B layout instead of masks.

Inputs: geometry exported from each board by scripts/export_geom.py
  python3 island_routed.py <revA geom.json> <revB geom.json>  -> island_routed.json, island_routed_*.png
Rev A: IMUs under the MCU, heater 4 x 120 R 1206 (0.86 W).
Rev B: corner island cut by two 1 mm milled slots; the copper-free edge bridges and the 2.2 mm
corner bridge are whatever the routed board has; heater 2 x 12 R 2010 in series (1.08 W). Only the
ICM-45686 (U20) is on the island; the BMI088 (U21) stays under the MCU, unheated.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import LineString

HERE = os.path.dirname(os.path.abspath(__file__))
REVA, REVB = sys.argv[1], sys.argv[2]
SLOTS = [((118.5, 76.5), (118.5, 86.7)), ((121.1, 89.5), (123.5, 89.5))]   # milled, 1.0 mm wide
V5 = 5.09


def run(geom, label, heater_refs, heater_w, slots, imu_refs=("U20", "U21")):
    sys.argv = [sys.argv[0], geom]
    import importlib, island as I
    I = importlib.reload(I)
    I.CASES = I.ENVELOPE
    I.HEATER_REFS = heater_refs
    I.IMU_REFS = imu_refs

    def slot_mask(*_):
        im = Image.new("1", (I.NF, I.NF), 0); d = ImageDraw.Draw(im)
        for a, c in slots:
            g = LineString([a, c]).buffer(0.5, 16)
            d.polygon([I.P(p) for p in g.exterior.coords], fill=1)
        return np.array(im, dtype=bool)
    I.ring_mask = slot_mask
    design = {"kind": "slot" if slots else None, "ring": (0, 0, 0, []) if slots else None}
    r = I.evaluate(label, design, heater_w=heater_w)
    # heat maps of the island corner, heater full, both flight cases
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    for cname, (amb, h, src) in I.ENVELOPE.items():
        if "bench" in cname:
            continue
        _, _, T = I.solve(design, amb, h, src, heater_w)
        fig, ax = plt.subplots(figsize=(5.2, 4.6))
        im = ax.imshow(T, extent=[I.X0, I.X0 + I.W, I.Y0 + I.W, I.Y0], cmap="inferno")
        ax.set_xlim(90, 125); ax.set_ylim(112, 75)
        for a, c in slots:
            ax.plot([a[0], c[0]], [a[1], c[1]], color="cyan", lw=2.5, solid_capstyle="round")
        ax.set_title(f"{label}: {cname}, heater full", fontsize=8)
        fig.colorbar(im, ax=ax, shrink=0.8, label="C")
        fig.savefig(os.path.join(HERE, f"island_routed_{label}_{'hot' if 'hot' in cname else 'cold'}.png"), dpi=110, bbox_inches="tight")
        plt.close(fig)
    return r


if __name__ == "__main__":
    res = [run(REVA, "revA", ("R44", "R45", "R46", "R47"), 4 * V5 ** 2 / 120, []),
           run(REVB, "revB", ("R44", "R45"), V5 ** 2 / 24, SLOTS, imu_refs=("U20",))]
    for r in res:
        print(r["design"], json.dumps(r["cases"]), "window", r["holdable_window_C"], r["window_width_C"])
    json.dump(res, open(os.path.join(HERE, "island_routed.json"), "w"), indent=1)
