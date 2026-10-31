"""Large-signal (averaged) load-step and start-up check of the chosen compensation.
Same plant as loop.py, with the switch-current clamp (current limit 4.5 A min) and a
0.3 A -> 2.5 A -> 0.3 A load step at 1 A/us."""
import subprocess, math
from loop import VREF, GMEA, AOL, GMPS, RTOP, RBOT, VOUT, FSW, CAP_NOM, CAP_DERATE, NCAP, ESR_EACH
RC, CC, CP = 9.09e3, 4.7e-9, 47e-12
cout = NCAP * CAP_NOM * CAP_DERATE
wn = math.pi * FSW; L = 1.0; C = 1 / (wn ** 2 * L); R = math.sqrt(L / C) / 1.0
net = f"""* averaged current-mode buck, transient
Vref ref 0 {VREF}
Gea 0 comp ref fb {GMEA}
Ro comp 0 {AOL / GMEA}
Rc comp cz {RC}
Cc cz 0 {CC}
Cp comp 0 {CP}
Ebuf h_in 0 comp 0 1
Rh h_in h1 {R}
Lh h1 h2 {L}
Ch h2 0 {C}
Bps 0 a I = min(max({GMPS}*v(h2), 0), 4.5)
Co a co {cout}
Resr co 0 {ESR_EACH / NCAP}
Rmin a 0 100
Iload a 0 PWL(0 0.25 1m 0.25 1.0022m 2.45 2m 2.45 2.0022m 0.25 3m 0.25)
Rt a fb {RTOP}
Rb fb 0 {RBOT}
.ic v(a)=0 v(comp)=0
.control
set noaskquit
tran 50n 3m uic
meas tran vss find v(a) at=0.99m
meas tran vmin min v(a) from=1m to=1.4m
meas tran vmax max v(a) from=2m to=2.4m
meas tran tstart when v(a)=4.9 rise=1
echo "vss = $&vss" > /tmp/step_out.txt
echo "vmin = $&vmin" >> /tmp/step_out.txt
echo "vmax = $&vmax" >> /tmp/step_out.txt
echo "tstart = $&tstart" >> /tmp/step_out.txt
wrdata /tmp/step_wave.txt v(a)
.endc
.end
"""
open("/opt/r/tmp/step.cir", "w").write(net)
subprocess.run(["chroot", "/opt/r", "ngspice", "-b", "/tmp/step.cir"], capture_output=True)
print(open("/opt/r/tmp/step_out.txt").read())
