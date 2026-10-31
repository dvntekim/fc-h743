#!/bin/bash
# Run Freerouting 1.9 on a DSN inside the KiCad chroot (under Xvfb); click away any warning dialog.
# Usage: fr_run.sh <dsn in /opt/r/tmp/...> <workdir name> [passes]
DSN=$1; WD=/opt/r/tmp/$2; MP=${3:-40}
rm -rf $WD && mkdir -p $WD && cp $DSN $WD/fc.dsn
(chroot /opt/r bash -c "cd /tmp/$2 && LD_LIBRARY_PATH=/usr/lib/jvm/java-25-openjdk-amd64/lib xvfb-run -a java -jar /opt/freerouting-1.9.0.jar -de fc.dsn -do fc.ses -mp $MP -mt 1" > $WD/fr.log 2>&1 &)
for i in $(seq 1 360); do
  sleep 10
  [ -f $WD/fc.ses ] && ! pgrep -f "^java -jar /opt/freerouting-1.9" >/dev/null && { echo "done after $((i*10)) s"; exit 0; }
  P=$(pgrep -f "^java -jar /opt/freerouting-1.9" | head -1); [ -z "$P" ] && continue
  if grep -q "normalization" $WD/logs/freerouting.log 2>/dev/null && [ ! -f $WD/.clicked ]; then
    D=$(tr '\0' '\n' < /proc/$P/environ | grep ^DISPLAY= | cut -d= -f2); X=$(tr '\0' '\n' < /proc/$P/environ | grep ^XAUTHORITY= | cut -d= -f2)
    sleep 3; chroot /opt/r bash -c "XAUTHORITY=$X DISPLAY=$D xdotool key Return" && touch $WD/.clicked
  fi
done
echo "timeout"
