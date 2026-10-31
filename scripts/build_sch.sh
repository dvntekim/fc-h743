#!/bin/bash
# Regenerate libs + schematic, run ERC, export PDF + PNG previews
set -e
cd "$(dirname "$0")"
python3 design.py >/dev/null
python3 gen_lib.py >/dev/null
python3 gen_sch.py
rm -rf /opt/r/tmp/fcsch && cp -r kicad /opt/r/tmp/fcsch
chroot /opt/r bash -c "cd /tmp/fcsch && kicad-cli sch erc --severity-all --format report -o erc.rpt fc.kicad_sch >/dev/null 2>&1; kicad-cli sch export pdf -o sch.pdf fc.kicad_sch >/dev/null 2>&1"
cp /opt/r/tmp/fcsch/erc.rpt /opt/r/tmp/fcsch/sch.pdf out/ 2>/dev/null || (mkdir -p out && cp /opt/r/tmp/fcsch/erc.rpt /opt/r/tmp/fcsch/sch.pdf out/)
grep "ERC messages" out/erc.rpt
rm -f out/sch-*.png; pdftoppm -r ${DPI:-45} -png out/sch.pdf out/sch
