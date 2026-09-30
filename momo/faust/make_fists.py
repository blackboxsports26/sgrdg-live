"""Ersetzt in einem Momo-Video die Hände durch geballte Fäuste (Stil der Vorlage), Ton bleibt erhalten.

Ablauf:
  MOMO_SRC=momo-original.mp4 python detect_hands.py        # erkennt die Hände je Bild -> dets.pkl
  MOMO_SRC=momo-original.mp4 python make_fists.py video momo-faust.mp4
  MOMO_SRC=momo-original.mp4 python make_fists.py stills prüfung.png 0.5 2.5 4.0   # Vorher/Nachher-Stichproben

manual.json enthält von Hand abgelesene Faustpositionen für Bilder, in denen sich die Hände per Farbe nicht finden
lassen (Hand auf dem Gesicht, verzerrte Bilder der Vorlage).
"""
import cv2, numpy as np, pickle, subprocess, sys, json, os
from scipy.signal import savgol_filter, medfilt

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.environ.get('MOMO_SRC', 'momo-original.mp4')          # das farbige Momo-Video (Eingabe)
DETS = os.environ.get('MOMO_DETS', os.path.join(HERE, 'dets.pkl'))   # Ergebnis von detect_hands.py
SKIN = (65, 199, 149)      # BGR von #95c741
INK = (22, 22, 22)
K = lambda n: np.ones((n, n), np.uint8)
PAL = np.array([(47, 46, 44), (251, 251, 251), (65, 199, 149), (34, 93, 194), (22, 22, 22)], np.int32)   # Gi, Weiß, Haut, Panzerrand, Umriss (BGR)

# ------------------------------------------------------------------ Verfolgung
def build_tracks(frames, max_dist=170, max_gap=10, min_len=3):
    tracks = []
    for t, fr in enumerate(frames):
        pairs = []
        for ti, tr in enumerate(tracks):
            lt = max(tr['obs'])
            if t - lt > max_gap: continue
            lc = np.array(frames[lt]['hands'][tr['obs'][lt]]['c'])
            for di, d in enumerate(fr['hands']):
                dist = np.linalg.norm(np.array(d['c']) - lc)
                if dist <= max_dist + 12 * (t - lt): pairs.append((dist, ti, di))
        pairs.sort()
        ut, ud = set(), set()
        for dist, ti, di in pairs:
            if ti in ut or di in ud: continue
            tracks[ti]['obs'][t] = di; ut.add(ti); ud.add(di)
        for di in range(len(fr['hands'])):
            if di not in ud: tracks.append(dict(obs={t: di}))
    return [tr for tr in tracks if len(tr['obs']) >= min_len]

def track_params(frames, tr, hint_scale=1.0):
    ts = sorted(tr['obs']); t0, t1 = ts[0], ts[-1]
    T = np.arange(t0, t1 + 1)
    def series(key, dim=None):
        xs = np.array(ts); 
        if dim is None: ys = np.array([frames[t]['hands'][tr['obs'][t]][key] for t in ts], float); return np.interp(T, xs, ys)
        ys = np.array([frames[t]['hands'][tr['obs'][t]][key] for t in ts], float)
        return np.stack([np.interp(T, xs, ys[:, k]) for k in range(dim)], 1)
    C = series('c', 2); Wp = series('w', 2); Uu = series('u', 2); A = series('area'); ASP = series('asp')
    def sm(a, win=7):
        if len(a) < 5: return a
        win = min(win, len(a) - (1 - len(a) % 2))
        return savgol_filter(a, win, 2, axis=0, mode='nearest') if win >= 5 else a
    C, Wp, Uu, A, ASP = sm(C), sm(Wp), sm(Uu), sm(A, 9), sm(ASP, 9)
    Uu = Uu / (np.linalg.norm(Uu, axis=1, keepdims=True) + 1e-9)
    r = np.clip(np.sqrt(np.maximum(A, 1) / np.pi) * 0.98 * hint_scale, 36, 64)
    F = Wp + Uu * r[:, None] * 0.98
    # Kompakte Flächen (geballte Hand, nur die Faust sichtbar): Mittelpunkt der Fläche nehmen
    w = np.clip((1.9 - ASP) / 0.5, 0, 1)[:, None]
    F = F * (1 - w) + C * w
    dv = F - C; nv = np.linalg.norm(dv, axis=1, keepdims=True)
    F = C + dv * np.minimum(1.0, (0.9 * r[:, None]) / np.maximum(nv, 1e-6))
    det = np.array([t in tr['obs'] for t in T])
    # Daumenseite: zum Kopf hin, gleitend stabilisiert
    sgn = np.zeros(len(T))
    for k, t in enumerate(T):
        hc = frames[t]['head']
        p = np.array([-Uu[k][1], Uu[k][0]])
        sgn[k] = np.sign(np.dot(p, (np.array(hc) - F[k])) ) if hc is not None else 0
    sgn = medfilt(np.where(sgn == 0, 1, sgn), 9 if len(sgn) >= 9 else 1)
    return dict(T=T, F=F, r=r, u=Uu, s=sgn, det=det)

# ------------------------------------------------------------------ Faust zeichnen
def draw_fist(img, cx, cy, r, ux, uy, s, SS=3):
    R = int(2.2 * r); x0, y0 = int(round(cx)) - R, int(round(cy)) - R
    size = 2 * R
    h, w = img.shape[:2]
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(w, x0 + size), min(h, y0 + size)
    if xb <= xa or yb <= ya: return
    col = np.zeros((size * SS, size * SS, 3), np.uint8); al = np.zeros((size * SS, size * SS), np.uint8)
    px, py = -uy * s, ux * s
    cxp, cyp = cx - x0, cy - y0
    def P(u, p): return ((cxp + ux * u + px * p) * SS, (cyp + uy * u + py * p) * SS)
    def circ(u, p, rad, c):
        ctr = P(u, p); q = (int(round(ctr[0])), int(round(ctr[1]))); rr = int(round(rad * SS))
        cv2.circle(col, q, rr, c, -1, cv2.LINE_AA); cv2.circle(al, q, rr, 255, -1, cv2.LINE_AA)
    def line(a, b, wpx, c):
        A_ = P(*a); B_ = P(*b); t = max(1, int(round(wpx * SS)))
        cv2.line(col, (int(A_[0]), int(A_[1])), (int(B_[0]), int(B_[1])), c, t, cv2.LINE_AA)
        cv2.line(al, (int(A_[0]), int(A_[1])), (int(B_[0]), int(B_[1])), 255, t, cv2.LINE_AA)
    ol = max(3.6, 0.105 * r)
    FP = [(-0.577, ), (-0.192, ), (0.192, ), (0.577, )]
    body = [(-0.08 * r, 0.0, r)] + [(0.615 * r, f[0] * r, 0.375 * r) for f in FP]
    for u, p, rad in body: circ(u, p, rad + ol, INK)
    for u, p, rad in body: circ(u, p, rad, SKIN)
    # Finger-Trennlinien und Falte
    lw = max(2.4, 0.07 * r)
    for k in range(3):
        m = (FP[k][0] + FP[k + 1][0]) / 2 * r
        line((0.40 * r, m), (0.90 * r, m), lw, INK)
    pts = [P(0.346 * r, -0.885 * r), P(0.23 * r, 0), P(0.346 * r, 0.885 * r)]
    curve = []
    for tt in np.linspace(0, 1, 18):
        x = (1 - tt) ** 2 * pts[0][0] + 2 * (1 - tt) * tt * pts[1][0] + tt ** 2 * pts[2][0]
        y = (1 - tt) ** 2 * pts[0][1] + 2 * (1 - tt) * tt * pts[1][1] + tt ** 2 * pts[2][1]
        curve.append([int(x), int(y)])
    cv2.polylines(col, [np.array(curve, np.int32)], False, INK, max(1, int(lw * SS)), cv2.LINE_AA)
    cv2.polylines(al, [np.array(curve, np.int32)], False, 255, max(1, int(lw * SS)), cv2.LINE_AA)
    # Daumen quer über den Fingern
    tc = P(0.115 * r, -0.46 * r); ang = np.degrees(np.arctan2(py, px))
    axes = (int(0.58 * r * SS), int(0.36 * r * SS))
    cv2.ellipse(col, (int(tc[0]), int(tc[1])), (axes[0] + int(ol * SS), axes[1] + int(ol * SS)), ang, 0, 360, INK, -1, cv2.LINE_AA)
    cv2.ellipse(col, (int(tc[0]), int(tc[1])), axes, ang, 0, 360, SKIN, -1, cv2.LINE_AA)
    cv2.ellipse(al, (int(tc[0]), int(tc[1])), (axes[0] + int(ol * SS), axes[1] + int(ol * SS)), ang, 0, 360, 255, -1, cv2.LINE_AA)
    colD = cv2.resize(col, (size, size), interpolation=cv2.INTER_AREA).astype(np.float32)
    alD = cv2.resize(al, (size, size), interpolation=cv2.INTER_AREA).astype(np.float32)[..., None] / 255.0
    sub = img[ya:yb, xa:xb].astype(np.float32)
    cs = colD[ya - y0:yb - y0, xa - x0:xb - x0]; asub = alD[ya - y0:yb - y0, xa - x0:xb - x0]
    img[ya:yb, xa:xb] = np.clip(sub * (1 - asub) + cs * asub, 0, 255).astype(np.uint8)

# ------------------------------------------------------------------ Bild bearbeiten
MANUAL = json.load(open(os.path.join(HERE, 'manual.json')))['windows'] if os.path.exists(os.path.join(HERE, 'manual.json')) else []
FPS_ = 30.0

def manual_hands(i, frames):
    """Handpositionen aus manual.json für Bild i: (aktiv, Liste von (x, y, r, ux, uy, s))."""
    t = i / FPS_
    for w in MANUAL:
        if w['t0'] - 1e-6 <= t <= w['t1'] + 1e-6:
            out = []
            for kf in w['hands']:
                ts = [k[0] for k in kf]
                x = np.interp(t, ts, [k[1] for k in kf]); y = np.interp(t, ts, [k[2] for k in kf]); a = np.radians(np.interp(t, ts, [k[3] for k in kf]))
                ux, uy = np.cos(a), np.sin(a)
                hc = frames[i]['head']
                s = 1.0
                if hc is not None:
                    s = 1.0 if np.dot([-uy, ux], [hc[0] - x, hc[1] - y]) >= 0 else -1.0
                out.append((x, y, w.get('r', 50), ux, uy, s))
            return True, out
    return False, []

def edit_frame(i, f, frames, tp):
    fr = frames[i]
    man_on, man = manual_hands(i, frames)
    H, W = f.shape[:2]
    mask = np.zeros((H, W), np.uint8)
    for h in fr['hands']:
        m = cv2.imdecode(np.frombuffer(h['mask'], np.uint8), cv2.IMREAD_GRAYSCALE)
        mask |= (m > 0).astype(np.uint8)
    mask = cv2.dilate(mask, K(13))
    active = []
    for p in ([] if man_on else tp):
        k = i - p['T'][0]
        if 0 <= k < len(p['T']):
            active.append((p, k))
            if not p['det'][k]:
                cv2.circle(mask, (int(p['F'][k][0]), int(p['F'][k][1])), int(p['r'][k] * 1.05), 1, -1)
    for (x, y, r, ux, uy, sg) in man:
        cv2.circle(mask, (int(x), int(y)), int(r * 1.15), 1, -1)
    out = f.copy()
    if mask.any():
        # Füllung mit der Farbe des nächsten unveränderten Pixels: scharfe Kanten, Gürtel/Gi setzen sich fort
        src = (mask > 0).astype(np.uint8)
        _, lab = cv2.distanceTransformWithLabels(src, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
        zero_idx = np.flatnonzero((src == 0).ravel())
        cols = f.reshape(-1, 3)[zero_idx]
        sel = mask > 0
        out[sel] = cols[lab[sel] - 1]
    for p, k in active:
        draw_fist(out, p['F'][k][0], p['F'][k][1], p['r'][k], p['u'][k][0], p['u'][k][1], p['s'][k])
    for (x, y, r, ux, uy, sg) in man:
        draw_fist(out, x, y, r, ux, uy, sg)
    return out

if __name__ == '__main__':
    d = pickle.load(open(DETS, 'rb')); frames = d['frames']
    tracks = build_tracks(frames)
    tp = [track_params(frames, tr) for tr in tracks]
    print(len(tracks), 'Hand-Spuren')
    mode = sys.argv[1]
    cap = cv2.VideoCapture(SRC); fps = d['fps']
    if mode == 'stills':
        out = sys.argv[2]; ts = [float(x) for x in sys.argv[3:]]; rows = []
        for t in ts:
            i = int(round(t * fps)); cap.set(cv2.CAP_PROP_POS_FRAMES, i); ok, f = cap.read()
            e = edit_frame(i, f, frames, tp)
            ys, xs = np.where(f.min(axis=2) < 225); x0 = max(0, min(1920 - 760, int(np.median(xs)) - 380))
            a = cv2.resize(f[:, x0:x0 + 760], (400, int(400 * 1088 / 760))); b = cv2.resize(e[:, x0:x0 + 760], (400, int(400 * 1088 / 760)))
            cv2.putText(a, f"{t:.2f}", (6, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            rows.append(b if os.environ.get('ONLY_EDIT') else np.vstack([a, b]))
        cols = int(os.environ.get('COLS', '0'))
        if cols:
            while len(rows) % cols: rows.append(np.full_like(rows[0], 255))
            cv2.imwrite(out, np.vstack([np.hstack(rows[j:j + cols]) for j in range(0, len(rows), cols)]))
        else:
            cv2.imwrite(out, np.hstack(rows))
    elif mode == 'video':
        outp = sys.argv[2]
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '1920x1088', '-r', str(fps), '-i', '-',
                               '-i', SRC, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt', 'yuv420p',
                               '-c:a', 'copy', '-movflags', '+faststart', outp], stdin=subprocess.PIPE)
        for i in range(d['N']):
            ok, f = cap.read()
            if not ok: break
            ff.stdin.write(edit_frame(i, f, frames, tp).tobytes())
        ff.stdin.close(); ff.wait(); print('Video:', outp)
