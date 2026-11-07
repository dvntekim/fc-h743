"""Second sweep: operating envelope (bench 25 C + flight 15-35 C), in-place slot island vs an island
moved away from the MCU, heater 0.86 W (4 x 120 R) and 1.5 W (4 x 68 R)."""
import json, sys, os
sys.argv = [sys.argv[0], sys.argv[1]]
import island as I
I.CASES = I.ENVELOPE
out = []
designs = {
    "revA": {"kind": None},
    "inplace_slot_11x9": {"kind": "slot", "ring": (5.5, 4.5, 1.0, I.necks_for(5.5, 4.5, 1.0, 1.0)), "heater_moved": True},
}
# relocated islands (centres in free-ish copper away from the MCU and the buck); slot ring, two 1 mm bridges
for name, (cx, cy) in {"moved_top_right": (113.0, 92.0), "moved_bottom_right": (113.0, 108.5)}.items():
    hx, hy, w = 5.0, 4.0, 1.0
    necks = [(cx - hx - w / 2, cy, 1.0), (cx + hx + w / 2, cy, 1.0)]
    designs[name] = {"kind": "slot", "ring": (hx, hy, w, necks), "center": (cx, cy)}
for name, d in designs.items():
    for hw in (I.HEATER_W, 1.5):
        r = I.evaluate(f"{name}_{hw:.2f}W", d, heater_w=hw, plot=(hw == I.HEATER_W))
        out.append(r)
        print(name, f"{hw:.2f} W", {k.split(':')[0]: (v['imu_heater_off_C'], v['imu_heater_full_C']) for k, v in r['cases'].items()},
              "window", r["holdable_window_C"], "w", r["window_width_C"], flush=True)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "island_envelope.json"), "w"), indent=1)
