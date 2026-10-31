#!/bin/zsh
# Build PX4 for the fch743 board and run it on Simantic against the netlist-generated scenario.
# Two targets: dvntekim_fch743 (the hardware build) and dvntekim_fch743sim, an exact copy whose
# only change is CONFIG_MMCSD_SDIOWAIT_WRCOMPLETE off. Simantic's SDMMC model never raises the
# D0-busy-end interrupt, so with it on every SD block write waits out a 0.5 s timeout.
source ~/.zshrc 2>/dev/null
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
LOG=~/drone/fch743/sim-run.log
{
  echo "== $(date)"
  cd ~/drone/PX4-Autopilot || exit 1
  source .venv/bin/activate
  make dvntekim_fch743_default 2>&1 | tail -15
  echo "== hw build exit ${pipestatus[1]}"
  rm -rf boards/dvntekim/fch743sim && cp -R boards/dvntekim/fch743 boards/dvntekim/fch743sim
  sed -i '' -e 's|boards/dvntekim/fch743/nuttx-config|boards/dvntekim/fch743sim/nuttx-config|' \
            -e 's|^CONFIG_MMCSD_SDIOWAIT_WRCOMPLETE=y|# CONFIG_MMCSD_SDIOWAIT_WRCOMPLETE is not set|' \
            boards/dvntekim/fch743sim/nuttx-config/nsh/defconfig
  sed -i '' -e 's|boards/dvntekim/fch743/nuttx-config|boards/dvntekim/fch743sim/nuttx-config|' boards/dvntekim/fch743sim/nuttx-config/bootloader/defconfig
  make dvntekim_fch743sim_default 2>&1 | tail -15
  echo "== sim build exit ${pipestatus[1]}"
  ls -la build/dvntekim_fch743sim_default/dvntekim_fch743sim_default.elf
  cd ~/drone/fch743/sim/simantic || exit 1
  gunzip -kf card.img.gz
  python3 tests/check_peers_offline.py
  sim run --scenario scenario.yaml --ascii --output console.txt --frames frames.txt --trace-symbol arm_hardfault --trace-symbol _assert > trace.txt 2>&1; echo "== sim exit $?"
  grep -v '^\s*$' trace.txt | tail -60
  echo "== console (first 200 lines)"
  head -200 console.txt
  echo "== Done. You can close this window."
} 2>&1 | tee $LOG
