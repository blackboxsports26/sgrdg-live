import cv2, numpy as np

K = lambda n: np.ones((n, n), np.uint8)

def masks(f):
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)
    h, s, v = [hsv[..., i].astype(np.int16) for i in range(3)]
    green = ((h >= 30) & (h <= 55) & (s > 70) & (v > 80)).astype(np.uint8)
    green = cv2.morphologyEx(green, cv2.MORPH_OPEN, K(3))
    orange = ((h >= 5) & (h <= 20) & (s > 110) & (v > 90)).astype(np.uint8)
    dark = (v < 95).astype(np.uint8)
    gi = cv2.morphologyEx(dark, cv2.MORPH_OPEN, K(13))      # dünne Umrisse fallen weg, Gi/Hose bleiben
    return green, orange, gi

def analyze(f, min_area=350):
    green, orange, gi = masks(f)
    nonwhite = (f.min(axis=2) < 225)
    ys, xs = np.where(nonwhite)
    top, bot = np.percentile(ys, 0.3), np.percentile(ys, 99.7)
    fh = bot - top
    n, lab, st, cen = cv2.connectedComponentsWithStats(green, connectivity=4)
    comps = [i for i in range(1, n) if st[i, 4] >= min_area]
    role = {}
    for i in comps:
        if cen[i][1] > top + 0.80 * fh: role[i] = 'foot'
    # Kopf: größte Fläche, die ganz oben beginnt
    cand = [i for i in comps if i not in role and st[i, 1] < top + 0.13 * fh and st[i, 4] > 15000]
    head = max(cand, key=lambda i: st[i, 4]) if cand else None
    if head is not None:
        role[head] = 'head'
        cs, _ = cv2.findContours((lab == head).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        hull = np.zeros_like(gi); cv2.fillPoly(hull, [cv2.convexHull(max(cs, key=cv2.contourArea))], 1)
        ng, gl, gs, gc = cv2.connectedComponentsWithStats(gi, connectivity=8)
        drop = np.zeros(ng, np.uint8)
        for k in range(1, ng):
            cx_, cy_ = int(gc[k][0]), int(gc[k][1])
            if gs[k, 4] < 3500 and hull[cy_, cx_]: drop[k] = 1   # Pupillen/Brauen: klein und mitten im Kopf
        gi = gi * (1 - drop[gl])
    # Panzer: berührt den orangen Rand
    od = cv2.dilate(orange, K(9))
    for i in comps:
        if i in role: continue
        if od[lab == i].mean() > 0.12: role[i] = 'shell'
    # Panzerfelder liegen als Gruppe (dünne Linien dazwischen) dicht beieinander
    free = [i for i in comps if i not in role]
    dl = {i: cv2.dilate((lab == i).astype(np.uint8), K(11)) for i in free}
    seen = set()
    for i in free:
        if i in seen: continue
        grp, stack = [i], [i]; seen.add(i)
        while stack:
            a = stack.pop()
            for j in free:
                if j not in seen and (dl[a] & (lab == j)).any(): seen.add(j); grp.append(j); stack.append(j)
        tot = sum(int(st[k, 4]) for k in grp)
        if tot > 28000 or (len(grp) >= 3 and tot > 18000):
            for k in grp: role[k] = 'shell'
    # Hals
    if head is not None:
        hx, hy, hw, hh = st[head, :4]
        for i in comps:
            if i in role: continue
            cx, cy = cen[i]
            if abs(cx - (hx + hw / 2)) < 0.25 * hw and hy + 0.90 * hh < cy < hy + 1.15 * hh and st[i, 4] < 0.12 * st[head, 4]:
                role[i] = 'neck'
    gid = cv2.dilate(gi, K(57))
    cand = []
    for i in comps:
        if i in role: continue
        m = lab == i
        touch = int((gid[m] > 0).sum())
        if touch < 40 or st[i, 4] >= 26000: continue
        cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        (_, _), (rw, rh), _ = cv2.minAreaRect(max(cs, key=cv2.contourArea))
        if min(rw, rh) < 24 and max(rw, rh) / max(min(rw, rh), 1) > 3: continue   # dünner Streifen (Panzerrand)
        cand.append(i)
    # Bruchstücke einer Hand zusammenfassen
    dil = {i: cv2.dilate((lab == i).astype(np.uint8), K(21)) for i in cand}
    od_contact = cv2.dilate(orange, K(11))
    groups, used = [], set()
    for i in cand:
        if i in used: continue
        g = [i]; used.add(i); stack = [i]
        while stack:
            a = stack.pop()
            for j in cand:
                if j not in used and (dil[a] & (lab == j)).any(): used.add(j); g.append(j); stack.append(j)
        groups.append(g)
    out = []
    for g in groups:
        m = np.isin(lab, g).astype(np.uint8)
        area = int(m.sum())
        if area < 900: continue
        # Streifen am Panzerrand: berühren den orangen Rand auf langer Strecke (echte Hände höchstens ~210 px)
        contact = int(((cv2.dilate(m, K(11)) > 0) & (od_contact > 0)).sum())
        cs2, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        (_, _), (rw2, rh2), _ = cv2.minAreaRect(max(cs2, key=cv2.contourArea))
        asp = max(rw2, rh2) / max(min(rw2, rh2), 1)
        if contact >= 260 and (asp >= 2.6 or area > 12000): continue
        yy, xx = np.where(m)
        C = np.array([xx.mean(), yy.mean()])
        # Ansatzpunkt am Ärmel (Handgelenk): Handpixel nahe am Gi
        near = (cv2.dilate(m, K(5)) > 0) & (cv2.dilate(gi, K(41)) > 0)
        wy, wx = np.where(near)
        if len(wx) > 20:
            Wp = np.array([wx.mean(), wy.mean()])
        else:
            Wp = C.copy()
        u = C - Wp
        if np.linalg.norm(u) < 6:
            cov = np.cov(np.stack([xx, yy])); w_, v_ = np.linalg.eigh(cov); u = v_[:, 1]
        u = u / (np.linalg.norm(u) + 1e-9)
        proj = (np.stack([xx, yy], 1) - Wp) @ u
        L = float(np.percentile(proj, 99)); Wd = area / max(L, 1.0)
        out.append(dict(ids=g, area=area, c=C.tolist(), w=Wp.tolist(), u=u.tolist(), L=L, wid=float(Wd),
                        box=(int(xx.min()), int(yy.min()), int(xx.max()), int(yy.max()))))
    info = dict(top=float(top), bot=float(bot), head=None if head is None else int(head))
    return dict(hands=out, info=info, lab=lab, role=role, stats=st, gi=gi)
