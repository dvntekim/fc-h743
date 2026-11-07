"""Time-domain model of PX4's IMU heater loop on the rev B island.

Plant (two thermal nodes):
  island   C_i dT_i/dt = P_heater - (T_i - T_env)/R_i - (T_i - T_s)/R_s
  sensor   C_s dT_s/dt = (T_i - T_s)/R_s          (IMU die/package lag behind the heater, ~1 s)
  T_env is the island's heater-off temperature (from sim/thermal/island.py); it moves with the
  whole board's time constant (~90 s) when conditions change (bench -> takeoff -> prop wash).
Controller: PX4 src/drivers/heater/heater.cpp, as written:
  every 10 ms period: e = T_set - T_s; P_term = P*e; I_acc = clamp(I_acc + I*e, +-IMAX);
  duty = clamp(FF + P_term + I_acc, 0, 1); heater on for duty * 10 ms.
  Defaults: P = 1.0 /C, I = 0.025 /C per update, FF = 0.05, IMAX = 0.25.
Rev B as routed (island_routed.py on the routed copper: corner peninsula, 1 mm milled slots,
copper-free edge bridges, 2.2 mm corner bridge, heater 2 x 12 R 2010 in series = 1.08 W at 5.09 V):
  R_i = 66.7 C / 1.08 W = 61.8 K/W still air, 39.6 C / 1.08 W = 36.7 K/W prop wash;
  heater-off island temperature 45.6 C (bench 25 C), 18.1 C (flight 15 C), 40.2 C (flight 35 C);
  set point 51 C (inside the 45.6-57.8 C holdable window).
C_i ~ 0.3 J/K (5.5 x 13.4 mm of 1.6 mm board + two 2010 resistors + IMUs).

Run: python3 heater_loop.py -> heater_loop.json, heater_loop.png
"""
import json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DT = 0.01                     # controller period, s
C_I, R_S, C_S = 0.30, 3.0, 0.3    # J/K, K/W (heater->sensor), J/K  -> sensor lag tau ~ 0.9 s
P_MAX = 1.08                  # W, 2 x 12 R in series at 5.09 V
TAU_BOARD = 90.0              # s, whole-board thermal time constant


R_STILL, R_WASH = 61.8, 36.7    # K/W
T_SET0 = 51.0
ENV_COLD = {"bench": 45.6, "flight": 18.1}
ENV_HOT = {"bench": 45.6, "flight": 40.2}


def scenario(t, env, iso=1.0):
    """bench warm-up at 25 C for 300 s, takeoff into prop wash, flight until 900 s"""
    if t < 300:
        return R_STILL * iso, env["bench"]
    return R_WASH * iso, env["flight"]


def run(P=1.0, I=0.025, FF=0.05, IMAX=0.25, T_SET=T_SET0, env=None, t_end=900.0, iso=1.0, lag=1.0, cap=1.0):
    """iso scales the island's thermal resistance to the board (0.5 = half the isolation),
    lag scales the heater-to-sensor lag, cap scales the island heat capacity."""
    env = env or ENV_COLD
    C_I_, R_S_ = C_I * cap, R_S * lag
    n = int(t_end / DT)
    Ti = Ts = Te = 25.0
    Iacc = 0.0
    log = np.zeros((n, 4))
    for k in range(n):
        t = k * DT
        R_i, Te_target = scenario(t, env, iso)
        Te += (Te_target - Te) * DT / TAU_BOARD
        e = T_SET - Ts
        Iacc = min(max(Iacc + I * e, -IMAX), IMAX)
        duty = min(max(FF + P * e + Iacc, 0.0), 1.0)
        Ph = P_MAX * duty                       # the 10 ms PWM is far faster than the plant
        dTi = (Ph - (Ti - Te) / R_i - (Ti - Ts) / R_S_) / C_I_
        dTs = ((Ti - Ts) / R_S_) / C_S
        Ti += dTi * DT; Ts += dTs * DT
        log[k] = (t, Ts, duty, Te)
    return log


def metrics(log, T_SET=T_SET0):
    t, Ts = log[:, 0], log[:, 1]
    out = {}
    for name, (a, b) in {"bench hold (200-300 s)": (200, 300), "takeoff transient (300-420 s)": (300, 420),
                         "flight hold (600-900 s)": (600, 900)}.items():
        m = (t >= a) & (t < b)
        err = Ts[m] - T_SET
        out[name] = {"max_err_C": round(float(np.max(np.abs(err))), 2), "mean_err_C": round(float(np.mean(err)), 2),
                     "p2p_ripple_C": round(float(np.ptp(Ts[m][-2000:])), 3)}
    out["duty_flight_mean"] = round(float(np.mean(log[(t >= 600), 2])), 2)
    return out


if __name__ == "__main__":
    res = {}
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    cases = {
        "PX4 defaults, 15 C flight": {},
        "PX4 defaults, 35 C flight": {"env": ENV_HOT},
        "sensor lag x3": {"lag": 3.0},
        "island heat capacity x2": {"cap": 2.0},
        "island heat capacity /2": {"cap": 0.5},
        "island isolation x2 better": {"iso": 2.0},
        "island isolation x0.85": {"iso": 0.85},
        "island isolation x0.75": {"iso": 0.75},
        "island isolation x2 worse": {"iso": 0.5},
    }
    fig, ax = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    for label, kw in cases.items():
        log = run(**kw)
        res[label] = metrics(log)
        if label in ("PX4 defaults, 15 C flight", "PX4 defaults, 35 C flight", "island isolation x2 worse"):
            ax[0].plot(log[:, 0], log[:, 1], label=label, lw=0.8)
            ax[1].plot(log[:, 0], log[:, 2], lw=0.6)
        print(label, json.dumps(res[label]))
    ax[0].axhspan(T_SET0 - 1.5, T_SET0 + 1.5, color="g", alpha=0.1, label="+-1.5 C band")
    ax[0].set_ylabel("IMU temperature (C)"); ax[0].set_ylim(15, 60); ax[0].legend(fontsize=7)
    ax[1].set_ylabel("heater duty"); ax[1].set_xlabel("time (s): bench 0-300, takeoff at 300")
    fig.savefig(os.path.join(HERE, "heater_loop.png"), dpi=110, bbox_inches="tight")
    json.dump(res, open(os.path.join(HERE, "heater_loop.json"), "w"), indent=1)
