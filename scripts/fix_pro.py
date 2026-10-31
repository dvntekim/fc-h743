"""Write net classes (netclasses.json) and the JLCPCB 6-layer board rules into kicad/fc.kicad_pro.
pcbnew rewrites the project file with defaults when a script builds a fresh BOARD, so run this
after gen_pcb.py and gen_sch.py."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "kicad", "fc.kicad_pro")
d = json.load(open(p))
nc = json.load(open(os.path.join(HERE, "netclasses.json")))
d["net_settings"] = nc
rules = d.setdefault("board", {}).setdefault("design_settings", {}).setdefault("rules", {})
rules.update({"min_clearance": 0.1, "min_track_width": 0.1, "min_via_diameter": 0.35, "min_through_hole_diameter": 0.15,
              "min_via_annular_width": 0.1, "min_copper_edge_clearance": 0.3, "min_hole_clearance": 0.2,
              "min_hole_to_hole": 0.25, "min_resolved_spokes": 1, "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1,
              "min_text_height": 0.8, "min_text_thickness": 0.08, "min_silk_clearance": 0.0, "max_error": 0.005,
              "solder_mask_to_copper_clearance": 0.0, "use_height_for_length_calcs": True})
json.dump(d, open(p, "w"), indent=2)
print("project rules + net classes written")
