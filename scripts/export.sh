#!/bin/bash
# Fabrication + assembly outputs for JLCPCB, plus review renders.
#   fab/gerbers/*  + fab/fc-h743-gerbers.zip   Gerber X2 + Excellon drill
#   fab/bom_jlc.csv, fab/cpl_jlc.csv            JLC assembly BOM / placement
#   docs/schematic.pdf, docs/render_*.png        review material
set -e
cd "$(dirname "$0")"
W=/opt/r/tmp/fcexp
rm -rf $W && mkdir -p $W && cp -r kicad/. $W/
mkdir -p fab/gerbers docs
LAYERS="F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
chroot /opt/r bash -c "cd /tmp/fcexp && rm -rf g && mkdir g && \
  kicad-cli pcb export gerbers --layers $LAYERS --subtract-soldermask --use-drill-file-origin -o g/ fc.kicad_pcb && \
  kicad-cli pcb export drill --format excellon --excellon-units mm --excellon-zeros-format decimal \
      --excellon-oval-format alternate --excellon-separate-th --generate-map --map-format gerberx2 -o g/ fc.kicad_pcb && \
  kicad-cli pcb export pos --format csv --units mm --side both --exclude-dnp -o pos.csv fc.kicad_pcb && \
  kicad-cli sch export bom --fields 'Reference,Value,Footprint,LCSC,\${QUANTITY},\${DNP}' \
      --labels 'Designator,Comment,Footprint,LCSC,Qty,DNP' --group-by 'Value,Footprint,LCSC' \
      --ref-range-delimiter '' -o bom.csv fc.kicad_sch && \
  kicad-cli sch export pdf -o schematic.pdf fc.kicad_sch && \
  kicad-cli pcb export step --subst-models --force -o fc.step fc.kicad_pcb >/dev/null 2>&1 || true"
rm -f fab/gerbers/*; cp $W/g/* fab/gerbers/
( cd fab/gerbers && rm -f ../fc-h743-gerbers.zip && zip -q ../fc-h743-gerbers.zip * )
cp $W/schematic.pdf docs/schematic.pdf
[ -f $W/fc.step ] && cp $W/fc.step fab/fc-h743.step || true
python3 - "$W" <<'PY'
import csv, sys, os
W = sys.argv[1]
# BOM: JLC wants Comment, Designator, Footprint, LCSC Part #
rows = list(csv.DictReader(open(f"{W}/bom.csv")))
with open("fab/bom_jlc.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    n = 0
    for r in rows:
        if r.get("DNP", "").strip() or not r["LCSC"].strip():
            continue
        refs = r["Designator"].replace(" ", ",")
        w.writerow([r["Comment"], refs, r["Footprint"].split(":")[-1], r["LCSC"]]); n += 1
print("bom lines", n, "of", len(rows))
# CPL: Designator, Mid X, Mid Y, Layer, Rotation
lcsc_refs = set()
for r in rows:
    if r["LCSC"].strip() and not r.get("DNP", "").strip():
        lcsc_refs.update(r["Designator"].replace(" ", ",").split(","))
with open("fab/cpl_jlc.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    n = 0
    for r in csv.DictReader(open(f"{W}/pos.csv")):
        if r["Ref"] not in lcsc_refs:
            continue
        w.writerow([r["Ref"], f'{float(r["PosX"]):.4f}mm', f'{float(r["PosY"]):.4f}mm',
                    "Top" if r["Side"] == "top" else "Bottom", f'{float(r["Rot"]) % 360:.0f}']); n += 1
print("cpl parts", n)
PY
ls fab fab/gerbers | head -40
