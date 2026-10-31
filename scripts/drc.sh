#!/bin/bash
# run KiCad DRC on the board in the chroot and summarise
chroot /opt/r bash -c "cd /tmp/fcpcb/kicad && kicad-cli pcb drc --severity-all --schematic-parity --format json -o /tmp/fcpcb/drc.json fc.kicad_pcb >/dev/null 2>&1"
cp /opt/r/tmp/fcpcb/drc.json out/drc.json; cp out/drc.json drc_last.json
python3 - <<'PY'
import json,collections
d=json.load(open('out/drc.json'))
print('violations',len(d['violations']),'unconnected',len(d['unconnected_items']),'parity',len(d.get('schematic_parity',[])))
c=collections.Counter((v['severity'],v['type']) for v in d['violations']); print(c.most_common(20))
n=collections.Counter()
for u in d['unconnected_items']:
    n[u['items'][0]['description'].split('[')[-1].split(']')[0]]+=1
print(n.most_common(40))
PY
