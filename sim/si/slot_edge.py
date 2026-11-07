"""Rev B: impedance of a signal track running beside an island slot (atlc).

The routing keepout puts a track edge >= 0.32 mm from the slot edge, and every copper layer
(including the In1/In4 GND planes) pulls back 0.3 mm from the slot, so a track at the keepout
limit has its reference plane ending ~0.02 mm beyond its own edge. This sweeps the track-to-slot
distance s for the two cases on the board: In2 stripline (In1/In4 planes) and F.Cu microstrip
(In1 plane), and compares against the same track far from any slot.

Run: python3 slot_edge.py -> slot_edge.json
"""
import json, os
import xsec
from xsec import Canvas, T_CU_IN, T_CU_OUT, T_MASK, H_PP, H_CORE, H_MID

W = 0.127
PULL = 0.3          # copper pull-back from the slot edge (fab rule, every layer)
CANVAS = 4.0
XM = 2.0            # track centre (the constructors centre it on the canvas)


def in2_near_slot(s):
    c = xsec.stripline_in2("s", W, None, width=CANVAS, coplanar=False)
    if s is not None:
        xs = XM + W / 2 + s                      # slot edge: air through the full stack beyond it
        c.a[:, xsec.n(xs):] = xsec.COL["air"]
        # planes stop PULL short of the slot edge: clear [xs-PULL, xs) on the plane rows
        H = c.H
        for y0, y1 in ((0, T_CU_IN), (c.H * xsec.PX - T_CU_IN, c.H * xsec.PX)):
            r0, r1 = H - xsec.n(y1), H - xsec.n(y0)
            c.a[max(r0, 0):r1, xsec.n(xs - PULL):xsec.n(xs)] = xsec.COL["core"]
    return c


def f_near_slot(s):
    c = xsec.microstrip("m", W, None, False, width=CANVAS)
    if s is not None:
        xs = XM + W / 2 + s
        c.a[:, xsec.n(xs):] = xsec.COL["air"]
        # In1 plane row: find green rows below the track and pull them back
        import numpy as np
        g = (c.a == xsec.COL["gnd"]).all(axis=2)
        rows = [r for r in range(c.H) if g[r, xsec.n(XM)]]
        for r in rows:
            c.a[r, xsec.n(xs - PULL):xsec.n(xs)] = xsec.COL["pp"]
    return c


if __name__ == "__main__":
    # the shared constructors centre the track; shift it to XM by re-centring the canvas width
    res = {}
    for lay, fn in (("In2", in2_near_slot), ("F", f_near_slot)):
        for s in (None, 1.0, 0.5, 0.32):
            v, _ = xsec.run(f"slot_{lay}_{'far' if s is None else s}", fn(s))
            res[f"{lay} s={'far' if s is None else s}"] = round(v.get("Zo", float('nan')), 1)
            print(lay, s, res[f"{lay} s={'far' if s is None else s}"], flush=True)
    json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "slot_edge.json"), "w"), indent=1)
