"""Time-domain model of PX4's IMU heater loop on the rev B island.

Plant (two thermal nodes):
  island   C_i dT_i/dt = P_heater - (T_i - T_env)/R_i - (T_i - T_s)/R_s
  sensor   C_s dT_s/dt = (T_i - T_s)/R_s          (IMU die/package lag behind the heater, ~1 s)
  T_env is the island's heater-off temperature (from sim/thermal/island.py); it moves with the
  whole board's time constant (~90 s) when conditions change (bench -> takeoff -> prop wash).
Controller: PX4 src/drivers/heater/heater.cpp, as written:
  every 10 ms period: e = T_set - T_s; P_term = P*e; I_acc = clamp(I_acc + I*e, +-IMAX);
  duty = clamp(FF + P_term + I_acc, 0, 1); heater on for duty * 10 ms.
  Defaults: P = 1.0 /C, I = 0.025 /C per update, FF = 0.05, IMAX = 0.25, T_set = 55 C.
Island numbers (moved_top_right, 1.5 W heater, island.py): R_i = 44 K/W still air, 27 K/W prop wash;
heater-off island temperature 48.3 C (bench 25 C), 19.8 C (flight 15 C), 42.8 C (flight 35 C).
C_i ~ 0.3 J/K (10 x 8 mm of 1.6 mm board + parts).

Run: python3 heater_loop.py -> heater_loop.json, heater_loop.png
"""
import json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DT = 0.01                     # controller period, s
C_I, R_S, C_S = 0.30, 3.0, 0.3    # J/K, K/W (heater->sensor), J/K  -> sensor lag tau ~ 0.9 s
P_MAX = 1.5                   # W, 4 x 68 R at 5.09 V
TAU_BOARD = 90.0              # s, whole-board thermal time constant


def scenario(t, env):
    """bench warm-up at 25 C for 300 s, takeoff into prop wash, flight until 900 s"""
    if t < 300:
        return 44.0, env["bench"]
    return 27.0, env["flight"]


def run(P=1.0, I=0.025, FF=0.05, IMAX=0.25, T_SET=55.0, env=None, t_end=900.0):
    env = env or {"bench": 48.3, "flight": 19.8}
    n = int(t_end / DT)
    Ti = Ts = Te = 25.0
    Iacc = 0.0
    log = np.zeros((n, 4))
    for k in range(n):
        t = k * DT
        R_i, Te_target = scenario(t, env)
        Te += (Te_target - Te) * DT / TAU_BOARD
        e = T_SET - Ts
        Iacc = min(max(Iacc + I * e, -IMAX), IMAX)
        duty = min(max(FF + P * e + Iacc, 0.0), 1.0)
        Ph = P_MAX * duty                       # the 10 ms PWM is far faster than the plant
        dTi = (Ph - (Ti - Te) / R_i - (Ti - Ts) / R_S) / C_I
        dTs = ((Ti - Ts) / R_S) / C_S
        Ti += dTi * DT; Ts += dTs * DT
        log[k] = (t, Ts, duty, Te)
    return log


def metrics(log, T_SET=55.0):
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
    fig, ax = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    for label, kw in {"PX4 defaults (P 1.0, I 0.025)": {}, "P 0.3, I 0.01, IMAX 0.25": {"P": 0.3, "I": 0.01},
                      "P 0.3, I 0.01, IMAX 0.25, flight 35 C": {"P": 0.3, "I": 0.01, "env": {"bench": 48.3, "flight": 42.8}}}.items():
        log = run(**kw)
        res[label] = metrics(log)
        ax[0].plot(log[:, 0], log[:, 1], label=label, lw=0.8)
        ax[1].plot(log[:, 0], log[:, 2], lw=0.6)
        print(label, json.dumps(res[label]))
    ax[0].axhspan(53.5, 56.5, color="g", alpha=0.1, label="+-1.5 C band")
    ax[0].set_ylabel("IMU temperature (C)"); ax[0].set_ylim(20, 65); ax[0].legend(fontsize=7)
    ax[1].set_ylabel("heater duty"); ax[1].set_xlabel("time (s): bench 0-300, takeoff at 300")
    fig.savefig(os.path.join(HERE, "heater_loop.png"), dpi=110, bbox_inches="tight")
    json.dump(res, open(os.path.join(HERE, "heater_loop.json"), "w"), indent=1)
