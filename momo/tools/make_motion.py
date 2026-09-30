#!/usr/bin/env python3
"""Überträgt eine mit extract_pose.py gelesene Bewegung auf Momos Proportionen.

Aufruf:  python make_motion.py pose_raw.json.gz ../motion.json --staff staff_keys.json

Jede Knochenrichtung der Vorlage wird übernommen, die Längen sind Momos (Einheit: Momos Körperhöhe = 1).
Koordinaten: x nach rechts, y nach unten, z weg von der Kamera (kleiner = näher), Ursprung = Beckenmitte.
"""
import argparse, gzip, json
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d
from scipy.signal import savgol_filter, medfilt

ap = argparse.ArgumentParser()
ap.add_argument("raw"); ap.add_argument("out")
ap.add_argument("--staff", required=True, help="staff_keys.json: Stab-Schlüsselbilder (Hand und Winkel)")
args = ap.parse_args()

raw = json.load((gzip.open if args.raw.endswith(".gz") else open)(args.raw, "rt"))
FPS = raw["fps"]
fr = raw["frames"]
N = len(fr)

# --------------------------------------------------------------------------- Rohdaten
IMG = np.array([f["img"] for f in fr], float)    # N,33,4 (x,y normiert, z, Sichtbarkeit)
WLD = np.array([f["world"] for f in fr], float)  # N,33,4 (Meter, Hüftmitte = Ursprung)

# Landmarken-Indizes (MediaPipe Pose)
NOSE, L_EAR, R_EAR = 0, 7, 8
L_SH, R_SH, L_EL, R_EL, L_WR, R_WR = 11, 12, 13, 14, 15, 16
L_PI, R_PI, L_IX, R_IX = 17, 18, 19, 20
L_HP, R_HP, L_KN, R_KN, L_AN, R_AN = 23, 24, 25, 26, 27, 28
L_HL, R_HL, L_FI, R_FI = 29, 30, 31, 32
PAIRS = [(1, 4), (2, 5), (3, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16), (17, 18), (19, 20),
         (21, 22), (23, 24), (25, 26), (27, 28), (29, 30), (31, 32)]

# --------------------------------------------------------------------------- links/rechts-Tausch beheben
# MediaPipe vertauscht links und rechts gern, wenn sich jemand wegdreht. Tausch, wenn er den Rumpf
# gegenüber dem Vorframe deutlich besser passen lässt.
TORSO = [L_SH, R_SH, L_HP, R_HP]
swaps = 0
for t in range(1, N):
    cur = WLD[t, TORSO, :3]
    prv = WLD[t - 1, TORSO, :3]
    sw = WLD[t, [R_SH, L_SH, R_HP, L_HP], :3]
    if np.sum((sw - prv) ** 2) < 0.6 * np.sum((cur - prv) ** 2):
        for a, b in PAIRS:
            WLD[t, [a, b]] = WLD[t, [b, a]]
            IMG[t, [a, b]] = IMG[t, [b, a]]
        swaps += 1
print("links/rechts korrigiert in", swaps, "Frames")

# --------------------------------------------------------------------------- glätten
def smooth(a, win=7, poly=2):
    out = np.empty_like(a)
    for j in range(a.shape[1]):
        for k in range(a.shape[2]):
            v = medfilt(a[:, j, k], 3)
            out[:, j, k] = savgol_filter(v, win, poly, mode="interp")
    return out

Wp = smooth(WLD[:, :, :3])
Ip = smooth(IMG[:, :, :3])

def unit(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.maximum(n, 1e-6)

# --------------------------------------------------------------------------- Momos Maße (Körperhöhe = 1)
M = dict(
    torso=0.22,         # Becken -> Brustmitte
    sh_half=0.105,      # halbe Schulterbreite
    hip_half=0.065,     # halbe Hüftbreite
    upper_arm=0.115, forearm=0.105,
    thigh=0.20, shank=0.20,
    neck=0.035, head_r=0.165,
    foot_len=0.095, foot_back=0.03, foot_drop=0.045,
    staff=1.0,
)

def at(name_l, name_r=None):
    return Wp[:, name_l]

hipC = (Wp[:, L_HP] + Wp[:, R_HP]) / 2
shC = (Wp[:, L_SH] + Wp[:, R_SH]) / 2

# Rumpfachsen: up (Wirbelsäule), lateral a (zur linken Körperseite), forward f
up = unit(shC - hipC)
a_raw = unit((Wp[:, L_SH] - Wp[:, R_SH]) + (Wp[:, L_HP] - Wp[:, R_HP]))
a_ax = unit(a_raw - np.sum(a_raw * up, -1, keepdims=True) * up)
f_ax = unit(np.cross(a_ax, up))   # zeigt dorthin, wohin der Körper blickt

# Kopf
earM = (Wp[:, L_EAR] + Wp[:, R_EAR]) / 2
ha = unit(Wp[:, L_EAR] - Wp[:, R_EAR])
hf = Wp[:, NOSE] - earM
hf = unit(hf - np.sum(hf * ha, -1, keepdims=True) * ha)
hu = unit(np.cross(hf, ha))
neck_dir = unit(0.6 * unit(earM - shC) + 0.4 * up)

P = np.zeros((N, 3))
C = P + up * M["torso"]
Ls = C + unit(Wp[:, L_SH] - Wp[:, R_SH]) * M["sh_half"]
Rs = C - unit(Wp[:, L_SH] - Wp[:, R_SH]) * M["sh_half"]
Lh = P + unit(Wp[:, L_HP] - Wp[:, R_HP]) * M["hip_half"]
Rh = P - unit(Wp[:, L_HP] - Wp[:, R_HP]) * M["hip_half"]

aspect = raw["W"] / raw["H"]

def bone(j0, j1, image_angle=False):
    """Knochenrichtung. Mit image_angle kommt der Winkel in der Bildebene aus den 2D-Bildpunkten
    (genauer als die 3D-Schätzung), die Verkürzung und die Tiefe bleiben aus den Weltkoordinaten."""
    w = Wp[:, j1] - Wp[:, j0]
    if not image_angle:
        return unit(w)
    e = unit((Ip[:, j1, :2] - Ip[:, j0, :2]) * np.array([aspect, 1.0]))
    mag = np.linalg.norm(w[:, :2], axis=-1, keepdims=True)
    return unit(np.concatenate([e * mag, w[:, 2:3]], axis=-1))

def chain(root, j0, j1, j2, l1, l2, image_angle=False):
    m = root + bone(j0, j1, image_angle) * l1
    e = m + bone(j1, j2, image_angle) * l2
    return m, e

Le, Lw = chain(Ls, L_SH, L_EL, L_WR, M["upper_arm"], M["forearm"], True)
Re, Rw = chain(Rs, R_SH, R_EL, R_WR, M["upper_arm"], M["forearm"], True)
Lk, La = chain(Lh, L_HP, L_KN, L_AN, M["thigh"], M["shank"])
Rk, Ra = chain(Rh, R_HP, R_KN, R_AN, M["thigh"], M["shank"])
Hd = C + neck_dir * (M["neck"] + M["head_r"])

def foot(an_w, hl, fi, an_m):
    v = unit(Wp[:, fi] - Wp[:, hl])
    down = np.array([0, 1.0, 0])
    toe = an_m + v * M["foot_len"] + down * (M["foot_drop"] - 0.01)
    heel = an_m - v * M["foot_back"] + down * M["foot_drop"]
    return heel, toe

Lhl, Lt = foot(Wp[:, L_AN], L_HL, L_FI, La)
Rhl, Rt = foot(Wp[:, R_AN], R_HL, R_FI, Ra)

# --------------------------------------------------------------------------- Bodenkontakt / Sprünge
# Abstand der tiefsten Sohle unter dem Becken = Beckenhöhe über dem Boden.
sole_y = np.maximum.reduce([La[:, 1], Ra[:, 1], Lhl[:, 1], Rhl[:, 1], Lt[:, 1], Rt[:, 1]]) + 0.03
pelvis_h = sole_y.copy()

# Sprünge: in den Bildkoordinaten liegt der tiefste Fuß im Flug über dem Boden, den er sonst berührt.
fy = np.maximum.reduce([Ip[:, L_AN, 1], Ip[:, R_AN, 1], Ip[:, L_FI, 1], Ip[:, R_FI, 1]])
body_img = medfilt(fy - Ip[:, NOSE, 1], 15)
win = int(0.8 * FPS)
floor = np.array([fy[max(0, t - win):t + win + 1].max() for t in range(N)])
air = np.clip((floor - fy) / np.maximum(body_img, 0.2) - 0.04, 0, None)
air = savgol_filter(air, 7, 2)
air = np.clip(air, 0, 0.6)
pelvis_h = pelvis_h + air

# Bühnenposition: die Kamera folgt der Figur, daher nur die Abweichung von der Bildmitte
hip_img_x = (Ip[:, L_HP, 0] + Ip[:, R_HP, 0]) / 2
root_x = (hip_img_x - 0.5) * aspect / np.maximum(body_img, 0.2) * 0.3
root_x = savgol_filter(np.clip(root_x, -0.6, 0.6), 9, 2)

# --------------------------------------------------------------------------- Stab
# Die Pose enthält den Stab nicht. staff_keys.json wurde deshalb von Hand aus dem Video abgelesen
# (alle 0,25 s: welche Hand hält ihn, wie liegt er in der Bildebene). Dazwischen wird interpoliert;
# Winkel sind Achsen (Modulo 180 Grad), darum wird der doppelte Winkel entwirrt und interpoliert.
keys = json.load(open(args.staff))["keys"]
tt = np.arange(N) / FPS
known = [k for k in keys if k[2] is not None]
kt = np.array([k[0] for k in known])
dbl = np.unwrap(2 * np.radians([k[2] for k in known]))
theta = PchipInterpolator(kt, dbl)(np.clip(tt, kt[0], kt[-1])) / 2

all_t = np.array([k[0] for k in keys])
who = [keys[int(np.abs(all_t - t).argmin())][1] for t in tt]

axis = np.stack([np.cos(theta), -np.sin(theta), np.zeros(N)], axis=-1)   # y zeigt nach unten
# Beim Wechsel der haltenden Hand wandert der Stab in ca. 0,15 s hinüber, statt zu springen
wR = np.array([{"L": 0.0, "B": 0.5, "R": 1.0}[w] for w in who])
wR = gaussian_filter1d(wR, 2.0)[:, None]
center = Lw * (1 - wR) + Rw * wR
mode = who
S0 = center - axis * M["staff"] / 2
S1 = center + axis * M["staff"] / 2

# --------------------------------------------------------------------------- ausgeben
KEYS = ["C", "Ls", "Rs", "Lh", "Rh", "Le", "Re", "Lw", "Rw", "Lk", "Rk", "La", "Ra",
        "Lhl", "Rhl", "Lt", "Rt", "Hd", "f", "a", "hf", "ha", "hu", "S0", "S1"]
VAL = dict(C=C, Ls=Ls, Rs=Rs, Lh=Lh, Rh=Rh, Le=Le, Re=Re, Lw=Lw, Rw=Rw, Lk=Lk, Rk=Rk, La=La, Ra=Ra,
           Lhl=Lhl, Rhl=Rhl, Lt=Lt, Rt=Rt, Hd=Hd, f=f_ax, a=a_ax, hf=hf, ha=ha, hu=hu, S0=S0, S1=S1)

frames = []
for t in range(N):
    row = [round(float(root_x[t]), 3), round(float(pelvis_h[t]), 3)]
    for k in KEYS:
        row.extend(round(float(x), 3) for x in VAL[k][t])
    frames.append(row)

pts = np.stack([VAL[k] for k in ("C", "Ls", "Rs", "Lh", "Rh", "Le", "Re", "Lw", "Rw", "Lk", "Rk", "La", "Ra",
                                   "Lhl", "Rhl", "Lt", "Rt", "Hd", "S0", "S1")], axis=1)   # N,K,3
abs_x = np.abs(root_x[:, None] + pts[:, :, 0]).max()
up_max = (pelvis_h[:, None] - pts[:, :, 1]).max()
bounds = dict(absX=round(float(abs_x) + 0.07, 3), up=round(float(up_max) + 0.17, 3))
print("Grenzen:", bounds)

out = dict(fps=FPS, dims=M, bounds=bounds, keys=["rootX", "pelvisH"] + KEYS, mode="".join(mode), frames=frames)
json.dump(out, open(args.out, "w"), separators=(",", ":"))
print("geschrieben:", args.out, N, "Frames,", round(N / FPS, 2), "s")
