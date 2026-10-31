"""Write the JLCPCB JLC06161H-3313D stackup into the board's (setup) block.
Layer roles: F sig | In1 GND | In2 sig | In3 sig | In4 GND | B sig.
Each signal layer sits 0.18-0.25 mm from its own GND plane; In2 and In3 face each other across
0.545 mm, which keeps their crosstalk low. Data: JLCPCB stackup table (via techoverflow.net,
2025-12-10); confirm on the JLC order page before ordering."""
import os, re
PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kicad", "fc.kicad_pcb")
D = [  # (name, type, thickness, material, er)
    ("F.SilkS", "Top Silk Screen", None, None, None),
    ("F.Paste", "Top Solder Paste", None, None, None),
    ("F.Mask", "Top Solder Mask", 0.01, None, None),
    ("F.Cu", "copper", 0.035, None, None),
    ("dielectric 1", "prepreg", 0.1834, "3313+1080", 4.021),
    ("In1.Cu", "copper", 0.0152, None, None),
    ("dielectric 2", "core", 0.25, "FR4", 4.6),
    ("In2.Cu", "copper", 0.0152, None, None),
    ("dielectric 3", "prepreg", 0.5448, "7628+2116+7628", 4.345),
    ("In3.Cu", "copper", 0.0152, None, None),
    ("dielectric 4", "core", 0.25, "FR4", 4.6),
    ("In4.Cu", "copper", 0.0152, None, None),
    ("dielectric 5", "prepreg", 0.1834, "1080+3313", 4.021),
    ("B.Cu", "copper", 0.035, None, None),
    ("B.Mask", "Bottom Solder Mask", 0.01, None, None),
    ("B.Paste", "Bottom Solder Paste", None, None, None),
    ("B.SilkS", "Bottom Silk Screen", None, None, None),
]
lines = ["\t\t(stackup"]
for name, typ, th, mat, er in D:
    s = f'\t\t\t(layer "{name}" (type "{typ}")'
    if th is not None:
        s += f" (thickness {th})"
    if mat:
        s += f' (material "{mat}") (epsilon_r {er}) (loss_tangent 0.02)'
    lines.append(s + ")")
lines += ['\t\t\t(copper_finish "ENIG")', "\t\t\t(dielectric_constraints no)", "\t\t)"]
block = "\n".join(lines) + "\n"
txt = open(PCB).read()
txt = re.sub(r"\t\t\(stackup\n.*?\n\t\t\)\n", "", txt, flags=re.S)
txt = txt.replace("\t(setup\n", "\t(setup\n" + block, 1)
open(PCB, "w").write(txt)
print("stackup written")
