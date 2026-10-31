#!/bin/bash
# sync sources into the KiCad chroot and run a pcbnew script there
set -e
cd "$(dirname "$0")"
mkdir -p /opt/r/tmp/fcpcb
rsync -a --delete --exclude out --exclude sim --exclude '*.png' --exclude '*.ses' --exclude '*.dsn' --exclude 'fr*.log' ./ /opt/r/tmp/fcpcb/
cp /opt/r/tmp/fcsch/fc.net /opt/r/tmp/fcpcb/fc.net 2>/dev/null || true
chroot /opt/r bash -c "cd /tmp/fcpcb && python3 $1" || echo "(python exit $? — pcbnew segfaults on teardown)"
rsync -a /opt/r/tmp/fcpcb/kicad/ ./kicad/
cp /opt/r/tmp/fcpcb/*.json ./ 2>/dev/null || true
