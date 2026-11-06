"""Coupling coefficient K vs edge gap for 0.127 mm tracks on F.Cu and In2.Cu (atlc)."""
import json, xsec
out = {}
for lay, fn in (("F", lambda g: xsec.microstrip("e", 0.127, g, False)), ("In2", lambda g: xsec.stripline_in2("e", 0.127, g, coplanar=False))):
    for g in (0.10, 0.15, 0.20, 0.30, 0.50):
        v, _ = xsec.run(f"k_{lay}_{g:.2f}", fn(g))
        out[f"{lay}:{g}"] = (v["Zeven"] - v["Zodd"]) / (v["Zeven"] + v["Zodd"])
        print(lay, g, round(out[f"{lay}:{g}"], 3), flush=True)
json.dump(out, open("k_sweep.json", "w"), indent=1)
