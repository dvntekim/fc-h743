"""TPS54360B 5 V buck: small-signal loop gain in ngspice (peak-current-mode model).

Model (TPS54360B datasheet SNVSB93, section 8.2.2.x "Loop compensation"):
  error amp gm = 350 uS, DC gain 10,000 V/V  -> Ro = 28.6 MOhm
  COMP -> switch current transconductance gm_ps = 12 A/V
  plant: Vout/Vcomp = gm_ps * (Rload || Zcout) * He(s)
  He(s): current-mode sampling double pole at fsw/2 (Ridley), Q swept 0.5..2 because the
  internal slope compensation is not published.
Run: python3 loop.py  (uses ngspice in the KiCad chroot)
"""
import itertools, json, math, os, re, subprocess

FSW = 597e3
VREF, GMEA, AOL, GMPS = 0.8, 350e-6, 1e4, 12.0
RTOP, RBOT = 53.6e3, 10e3
VOUT = VREF * (1 + RTOP / RBOT)
CAP_NOM, CAP_DERATE = 22e-6, 0.59      # CL21A226MAQNNNE 25 V X5R 0805 at 5 V DC bias (Samsung curve ~ -40%)
NCAP, ESR_EACH = 3, 0.005


def run(rc, cc, cp, iload, cout, q):
    ro = AOL / GMEA
    rl = VOUT / iload
    wn = math.pi * FSW
    # 2nd-order LPF for He: L = 1 H scaling; C = 1/(wn^2 L); R = sqrt(L/C)/Q
    L = 1.0; C = 1 / (wn ** 2 * L); R = math.sqrt(L / C) / q
    esr = ESR_EACH / NCAP
    net = f"""* loop gain
Vref ref 0 {VREF}
* error amplifier (OTA)
Gea 0 comp ref fb {GMEA}
Ro comp 0 {ro}
Rc comp cz {rc}
Cc cz 0 {cc}
Cp comp 0 {cp}
* sampling double pole on the control path
Ebuf h_in 0 comp 0 1
Rh h_in h1 {R}
Lh h1 h2 {L}
Ch h2 0 {C}
* power stage: current source into output impedance
Gps 0 a h2 0 {GMPS}
Rload a 0 {rl}
Co a co {cout}
Resr co 0 {esr}
* injection (Middlebrook): b = a + vinj
Vinj b a dc 0 ac 1
Rt b fb {RTOP}
Rb fb 0 {RBOT}
.control
set noaskquit
ac dec 200 100 3meg
let T = -v(a)/v(b)
let mag = db(T)
let ph = 180/pi*cphase(T)
meas ac fc when mag=0
meas ac pm find ph when mag=0
meas ac gm180 find mag when ph=-180
echo "fc = $&fc" > /tmp/loop_out.txt
echo "pm = $&pm" >> /tmp/loop_out.txt
echo "gm180 = $&gm180" >> /tmp/loop_out.txt
wrdata /tmp/loop_bode.txt mag ph
.endc
.end
"""
    open("/opt/r/tmp/loop.cir", "w").write(net)
    if os.path.exists("/opt/r/tmp/loop_out.txt"): os.remove("/opt/r/tmp/loop_out.txt")
    subprocess.run(["chroot", "/opt/r", "ngspice", "-b", "/tmp/loop.cir"], capture_output=True, text=True)
    out = open("/opt/r/tmp/loop_out.txt").read()
    vals = dict(re.findall(r"(\w+)\s*=\s*([-\d.e+]+)", out))
    fc = float(vals.get("fc", "nan")); pm = float(vals.get("pm", "nan"))
    pm = pm + 180 if pm < 0 else pm
    gm = -float(vals["gm180"]) if "gm180" in vals else float("inf")
    return fc, pm, gm


if __name__ == "__main__":
    cout_nom = NCAP * CAP_NOM * CAP_DERATE
    # first-pass design (TI equations): fc target 40 kHz
    fc_t = 40e3
    rc = 2 * math.pi * fc_t * VOUT * cout_nom / (GMEA * VREF * GMPS)
    cc = (VOUT / 3.5) * cout_nom / rc
    print(f"Vout {VOUT:.3f} V, Cout(eff) {cout_nom*1e6:.1f} uF -> Rc {rc/1e3:.2f}k, Cc {cc*1e9:.2f} nF")
    results = []
    for rc_e, cc_e, cp_e in [(13.3e3, 3.9e-9, 39e-12), (13.3e3, 4.7e-9, 39e-12), (9.09e3, 4.7e-9, 47e-12)]:
        rows = []
        for iload, cfac, q in itertools.product([0.3, 1.5, 3.5], [0.7, 1.0, 1.3], [0.5, 1.0, 2.0]):
            fc, pm, gm = run(rc_e, cc_e, cp_e, iload, cout_nom * cfac, q)
            rows.append(dict(iload=iload, cout_uF=round(cout_nom * cfac * 1e6, 1), q=q,
                             fc_kHz=round(fc / 1e3, 1), pm_deg=round(pm, 1), gm_dB=round(gm, 1)))
        worst = min(rows, key=lambda r: r["pm_deg"])
        print(f"Rc={rc_e/1e3:.2f}k Cc={cc_e*1e9:.1f}n Cp={cp_e*1e12:.0f}p: fc {min(r['fc_kHz'] for r in rows)}-"
              f"{max(r['fc_kHz'] for r in rows)} kHz, worst PM {worst['pm_deg']} deg at {worst}, "
              f"min GM {min(r['gm_dB'] for r in rows)} dB")
        results.append(dict(rc=rc_e, cc=cc_e, cp=cp_e, rows=rows))
    json.dump(results, open("loop_results.json", "w"), indent=1)
