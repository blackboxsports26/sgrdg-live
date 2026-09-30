/* Momo – Schildkröte im Strichstil, bewegt sich nach motion.json (siehe tools/make_motion.py).
 *
 * Die Figur ist ein 3D-Skelett (Einheit: Körperhöhe = 1; x rechts, y unten, z weg von der Kamera),
 * das mit Kapseln, Ellipsen und Kugel-Merkmalen gezeichnet wird. Dadurch dreht sie sich sauber von
 * vorn über die Seite zum Rücken. Teile werden nach Tiefe sortiert (Malerverfahren).
 */
(function (global) {
  'use strict';

  var OUT = '#141414', FILL = '#ffffff';

  // Farben: 'color' nach der farbigen Momo-Vorlage, 'line' = reiner Strichstil
  var PAL = {
    line: { skin: FILL, gi: FILL, giLine: OUT, belt: FILL, rim: FILL, dome: FILL, scute: OUT, rimLine: OUT,
            cheek: null, tongue: FILL, eye: FILL, staff: FILL },
    color: { skin: '#95c741', gi: '#2a2a2e', giLine: '#a4a4ad', belt: '#f7f6f7', rim: '#c25d22', dome: '#8fbf47',
             scute: '#3d6a1c', rimLine: '#6e3614', cheek: '#eea23a', tongue: '#e8707f', eye: FILL, staff: '#e7cc8f' }
  };

  // ---------------------------------------------------------------- Vektoren
  function add(a, b) { return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]; }
  function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
  function mul(a, s) { return [a[0] * s, a[1] * s, a[2] * s]; }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
  function len(a) { return Math.sqrt(dot(a, a)); }
  function norm(a) { var l = len(a) || 1; return [a[0] / l, a[1] / l, a[2] / l]; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  // ---------------------------------------------------------------- Daten
  function load(url) {
    return fetch(url).then(function (r) { return r.json(); }).then(function (d) {
      d.idx = {};
      d.keys.forEach(function (k, i) { d.idx[k] = i; });
      return d;
    });
  }

  // Zeile (Zahlenliste) -> Objekt mit Vektoren
  function unpack(d, row) {
    var o = { rootX: row[0], pelvisH: row[1] }, p = 2;
    for (var i = 2; i < d.keys.length; i++, p += 3) o[d.keys[i]] = [row[p], row[p + 1], row[p + 2]];
    return o;
  }

  // Zwischenwert zweier Frames (t in Sekunden)
  function rowAt(d, t) {
    var x = clamp(t * d.fps, 0, d.frames.length - 1), i = Math.floor(x), j = Math.min(i + 1, d.frames.length - 1), u = x - i;
    var a = d.frames[i], b = d.frames[j], r = new Array(a.length);
    for (var k = 0; k < a.length; k++) r[k] = a[k] + (b[k] - a[k]) * u;
    return { row: r, mode: d.mode.charAt(Math.round(x)) };
  }

  // ---------------------------------------------------------------- Zeichnen
  // opt: width, height, scale (px pro Körperhöhe), ground (y des Bodens), trail (Anzahl Vor-Frames)
  function draw(ctx, d, t, opt) {
    opt = opt || {};
    var W = opt.width, H = opt.height;
    var gy = opt.ground != null ? opt.ground : H * 0.92;
    // Größe so wählen, dass die ganze Bewegung (Stab, Arme, Sprünge) ins Bild passt
    var S = opt.scale || (d.bounds ? Math.min(0.485 * W / d.bounds.absX, (gy - 0.03 * H) / d.bounds.up) : H * 0.56);
    var cur = rowAt(d, t), f = unpack(d, cur.row), mode = cur.mode;
    var ox = W / 2 + f.rootX * S, oy = gy - f.pelvisH * S;
    var OL = Math.max(3, S * 0.0095);
    var M = d.dims;
    var pal = PAL[opt.style === 'line' ? 'line' : 'color'];

    function P(v) { return [ox + v[0] * S, oy + v[1] * S]; }

    ctx.save();
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';

    // --- Boden-Schatten
    var air = Math.max(0, f.pelvisH - soleDepth(f));
    ctx.fillStyle = 'rgba(20,20,20,' + (0.10 * (1 - Math.min(1, air * 2.5))).toFixed(3) + ')';
    ctx.beginPath();
    ctx.ellipse(ox, gy + S * 0.012, S * (0.20 - air * 0.12), S * 0.028, 0, 0, Math.PI * 2);
    ctx.fill();

    // ------------------------------------------------ Hilfsfunktionen fürs Zeichnen
    function seg(a, b) { ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); }

    // Kette aus Segmenten mit Umriss; erst alle schwarz, dann alle weiß -> kein Strich an den Gelenken
    function tube(pts, ws, fill) {
      ctx.strokeStyle = OUT;
      for (var i = 0; i < ws.length; i++) { ctx.lineWidth = ws[i] + 2 * OL; seg(pts[i], pts[i + 1]); }
      ctx.strokeStyle = fill || FILL;
      for (i = 0; i < ws.length; i++) { ctx.lineWidth = ws[i]; seg(pts[i], pts[i + 1]); }
    }

    function smoothPath(pts, k) {
      var n = pts.length; k = k || 0.18;
      ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]);
      for (var i = 0; i < n; i++) {
        var p0 = pts[(i - 1 + n) % n], p1 = pts[i], p2 = pts[(i + 1) % n], p3 = pts[(i + 2) % n];
        ctx.bezierCurveTo(p1[0] + (p2[0] - p0[0]) * k, p1[1] + (p2[1] - p0[1]) * k,
                          p2[0] - (p3[0] - p1[0]) * k, p2[1] - (p3[1] - p1[1]) * k, p2[0], p2[1]);
      }
      ctx.closePath();
    }

    function fillStroke(lw, fill) {
      ctx.fillStyle = fill || FILL; ctx.fill();
      ctx.strokeStyle = OUT; ctx.lineWidth = lw || OL; ctx.stroke();
    }

    // Querstrich (z. B. Saum) senkrecht zu einem Segment
    function cross2(a, b, at, halfLen, col) {
      var dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy) || 1;
      var px = -dy / l, py = dx / l, cx = lerp(a[0], b[0], at), cy = lerp(a[1], b[1], at);
      ctx.lineWidth = OL * 0.8; ctx.strokeStyle = col || OUT;
      seg([cx - px * halfLen, cy - py * halfLen], [cx + px * halfLen, cy + py * halfLen]);
    }

    var parts = [];
    function part(z, fn) { parts.push({ z: z, fn: fn }); }

    // ------------------------------------------------ Rumpf (Gi-Jacke, Gürtel, Revers)
    var up = norm(f.C), ax = f.a, fw = f.f;
    var cs = P(f.C), d2 = [cs[0] - ox, cs[1] - oy], dl = Math.hypot(d2[0], d2[1]);
    d2 = dl < 4 ? [0, -1] : [d2[0] / dl, d2[1] / dl];
    var pp = [-d2[1], d2[0]];
    function hw(A, B) {
      return Math.hypot(A * (ax[0] * pp[0] + ax[1] * pp[1]), B * (fw[0] * pp[0] + fw[1] * pp[1])) * S;
    }
    function sp(h) { return P(mul(up, h)); }
    function edge(h, A, B, s) { var c = sp(h), w = hw(A, B) * s; return [c[0] + pp[0] * w, c[1] + pp[1] * w]; }
    var prof = [[-0.085, 0.098, 0.082], [-0.03, 0.100, 0.084], [0.05, 0.097, 0.082],
                [0.13, 0.114, 0.088], [0.20, 0.120, 0.088], [0.235, 0.080, 0.066]];
    var torsoZ = f.C[2] / 2;

    part(torsoZ, function () {
      var pts = [], i;
      for (i = 0; i < prof.length; i++) pts.push(edge(prof[i][0], prof[i][1], prof[i][2], -1));
      for (i = prof.length - 1; i >= 0; i--) pts.push(edge(prof[i][0], prof[i][1], prof[i][2], 1));
      smoothPath(pts, 0.16); fillStroke(null, pal.gi);

      var facing = clamp((-fw[2] - 0.12) / 0.35, 0, 1);   // 1 = Vorderseite zur Kamera
      var back = clamp((fw[2] - 0.12) / 0.35, 0, 1);

      // Revers (über Kreuz) und Kragen
      if (facing > 0) {
        ctx.globalAlpha = facing; ctx.lineWidth = OL * 0.75; ctx.strokeStyle = pal.giLine;
        var B0 = 0.092;
        var cl = P(add(add(mul(up, 0.215), mul(ax, 0.042)), mul(fw, B0 * 0.85)));
        var cr = P(add(add(mul(up, 0.215), mul(ax, -0.042)), mul(fw, B0 * 0.85)));
        var bl = P(add(add(mul(up, 0.022), mul(ax, 0.038)), mul(fw, B0)));
        var br = P(add(add(mul(up, 0.022), mul(ax, -0.038)), mul(fw, B0)));
        seg(cl, br); seg(cr, bl);
        var nk = P(add(add(mul(up, 0.236), mul(fw, B0 * 0.8)), [0, 0, 0]));
        ctx.beginPath(); ctx.moveTo(cl[0], cl[1]); ctx.quadraticCurveTo(nk[0], nk[1] + S * 0.012, cr[0], cr[1]); ctx.stroke();
        ctx.globalAlpha = 1;
      }
      // Rückennaht
      if (back > 0) {
        ctx.globalAlpha = back * 0.8; ctx.lineWidth = OL * 0.65; ctx.strokeStyle = pal.giLine;
        seg(P(add(mul(up, 0.205), mul(fw, -0.09))), P(add(mul(up, -0.06), mul(fw, -0.084))));
        ctx.globalAlpha = 1;
      }

      // Gürtel
      var bh = 0.028, bA = 0.102, bB = 0.086;
      var L0 = edge(bh + 0.022, bA, bB, -1), R0 = edge(bh + 0.022, bA, bB, 1);
      var L1 = edge(bh - 0.022, bA, bB, -1), R1 = edge(bh - 0.022, bA, bB, 1);
      ctx.beginPath(); ctx.moveTo(L0[0], L0[1]); ctx.lineTo(R0[0], R0[1]); ctx.lineTo(R1[0], R1[1]); ctx.lineTo(L1[0], L1[1]); ctx.closePath();
      fillStroke(OL * 0.9, pal.belt);

      // Knoten und Gürtelenden (nur von vorn)
      if (facing > 0) {
        ctx.globalAlpha = facing;
        var kn = P(add(add(mul(up, bh), mul(fw, 0.092)), mul(ax, 0.018)));
        var dn = [-d2[0], -d2[1]], ang = [0.30, -0.22], lens = [0.135, 0.115];
        for (var e = 0; e < 2; e++) {
          var ca = Math.cos(ang[e]), sa = Math.sin(ang[e]);
          var dir = [dn[0] * ca - dn[1] * sa, dn[0] * sa + dn[1] * ca], nx = -dir[1], ny = dir[0];
          var w0 = S * 0.026, w1 = S * 0.03, l = S * lens[e];
          var a1 = [kn[0] + nx * w0, kn[1] + ny * w0], a2 = [kn[0] - nx * w0, kn[1] - ny * w0];
          var b1 = [kn[0] + dir[0] * l + nx * w1, kn[1] + dir[1] * l + ny * w1];
          var b2 = [kn[0] + dir[0] * l - nx * w1, kn[1] + dir[1] * l - ny * w1];
          ctx.beginPath(); ctx.moveTo(a1[0], a1[1]); ctx.lineTo(b1[0], b1[1]); ctx.lineTo(b2[0], b2[1]); ctx.lineTo(a2[0], a2[1]); ctx.closePath();
          fillStroke(OL * 0.85, pal.belt);
        }
        ctx.beginPath(); ctx.ellipse(kn[0], kn[1], S * 0.038, S * 0.032, Math.atan2(d2[1], d2[0]), 0, Math.PI * 2);
        fillStroke(OL * 0.9, pal.belt);
        ctx.globalAlpha = 1;
      }
    });

    // ------------------------------------------------ Panzer (Kuppel hinter dem Rücken)
    (function () {
      var back = mul(fw, -1), cen = add(mul(up, 0.105), mul(fw, -0.105)), rx = 0.150, ry = 0.175, T = 0.085;
      var layers = [0, 0.25, 0.5, 0.75, 1], N = 30;
      function disc(tt, sc) {
        var o = add(cen, mul(back, T * tt * 1.0 - 0.0)), s = sc * (1 - 0.30 * tt * tt), pts = [];
        for (var i = 0; i < N; i++) {
          var ph = i / N * Math.PI * 2;
          pts.push(P(add(add(o, mul(ax, rx * s * Math.cos(ph))), mul(up, ry * s * Math.sin(ph) + 0.0))));
        }
        return pts;
      }
      function poly(pts) { ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]); for (var i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]); ctx.closePath(); }
      part(torsoZ - fw[2] * 0.11, function () {
        var D = layers.map(function (tt) { return disc(tt, 1); }), i;
        ctx.strokeStyle = OUT; ctx.fillStyle = OUT; ctx.lineWidth = OL * 2;
        for (i = 0; i < D.length; i++) { poly(D[i]); ctx.stroke(); ctx.fill(); }
        // Von hinten liegt die Kuppel oben, von vorn der orange Rand
        var order = fw[2] > 0 ? [0, 1, 2, 3, 4] : [4, 3, 2, 1, 0];
        order.forEach(function (k) { ctx.fillStyle = k === 0 ? pal.rim : pal.dome; poly(D[k]); ctx.fill(); });

        var vis = clamp((fw[2] - 0.05) / 0.3, 0, 1);       // Rücken zur Kamera: Muster sichtbar
        function ring(tt, sc) { poly(disc(tt, sc)); }
        function onDisc(tt, sc, lat, upv) {
          var o = add(cen, mul(back, T * tt));
          return P(add(add(o, mul(ax, rx * sc * (1 - 0.30 * tt * tt) * lat)), mul(up, ry * sc * (1 - 0.30 * tt * tt) * upv)));
        }
        // Randfelder des orangen Rands
        ctx.lineWidth = OL * 0.6; ctx.strokeStyle = pal.rimLine; ctx.globalAlpha = fw[2] > 0 ? Math.max(vis, 0.6) : 0.85;
        for (i = 0; i < 18; i++) {
          var q = i / 18 * Math.PI * 2 + 0.17, ca = Math.cos(q), sa = Math.sin(q);
          seg(onDisc(0, 0.86, ca, sa), onDisc(0, 1.0, ca, sa));
        }
        ring(0, 0.86); ctx.stroke();
        ctx.globalAlpha = 1;
        if (vis > 0) {
          ctx.globalAlpha = vis; ctx.lineWidth = OL * 0.7; ctx.strokeStyle = pal.scute;
          ring(1, 0.80); ctx.stroke();
          var hx = [], k2;
          for (k2 = 0; k2 < 6; k2++) { var an = k2 / 6 * Math.PI * 2; hx.push([Math.cos(an) * 0.40, Math.sin(an) * 0.46]); }
          ctx.beginPath();
          hx.forEach(function (h, n) { var p = onDisc(1, 0.80, h[0], h[1]); n ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]); });
          ctx.closePath(); ctx.stroke();
          hx.forEach(function (h) {
            var n = Math.hypot(h[0] / 0.40, h[1] / 0.46);
            seg(onDisc(1, 0.80, h[0], h[1]), onDisc(1, 0.80, h[0] / 0.40 * 0.98, h[1] / 0.46 * 0.98));
          });
          ctx.globalAlpha = 1;
        }
      });
    })();

    // ------------------------------------------------ Kopf
    part(f.Hd[2] - 0.03, function () {
      var c = P(f.Hd), R = M.head_r * S;
      ctx.beginPath(); ctx.arc(c[0], c[1], R, 0, Math.PI * 2); fillStroke(OL * 1.05, pal.skin);

      var hf = norm(f.hf), ha = norm(f.ha), hu = norm(f.hu);
      // Merkmal auf der Kugeloberfläche: lokale Zeichnung in Kopfradien, korrekt perspektivisch verkürzt
      function onSphere(lat, upv, protrude, fn) {
        var fwd = Math.sqrt(Math.max(0.0001, 1 - lat * lat - upv * upv));
        var o = norm(add(add(mul(ha, lat), mul(hu, upv)), mul(hf, fwd)));
        var nz = -o[2];
        if (nz < 0.14) return;
        var e1 = sub(ha, mul(o, dot(ha, o))), e2 = sub(hu, mul(o, dot(hu, o)));
        var rr = 1 + (protrude || 0);
        ctx.save();
        ctx.transform(e1[0] * R, e1[1] * R, -e2[0] * R, -e2[1] * R, c[0] + o[0] * R * rr, c[1] + o[1] * R * rr);
        ctx.lineWidth = OL / R * 0.85;
        fn(1);   // ganz oder gar nicht: halbtransparente Augen am Kopfrand sehen wie Glas aus
        ctx.restore();
      }
      function ell(x, y, rx, ry) { ctx.beginPath(); ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2); }

      // Wangen (Rötel-Striche)
      [-1, 1].forEach(function (s) {
        onSphere(s * 0.74, -0.32, 0, function (al) {
          ctx.globalAlpha = al; ctx.beginPath(); ctx.ellipse(0, 0, 0.12, 0.068, 0, 0, Math.PI * 2);
          if (pal.cheek) { ctx.fillStyle = pal.cheek; ctx.fill(); } else { ctx.strokeStyle = OUT; ctx.lineWidth = OL / R * 0.6; ctx.stroke(); }
          ctx.globalAlpha = 1;
        });
      });
      // Augen: groß, mit Lichtpunkten
      [-1, 1].forEach(function (s) {
        onSphere(s * 0.43, 0.04, 0, function (al) {
          ctx.globalAlpha = al;
          ell(0, 0, 0.25, 0.28); ctx.fillStyle = pal.eye; ctx.fill(); ctx.strokeStyle = OUT; ctx.stroke();
          ell(0.008, 0.012, 0.19, 0.225); ctx.fillStyle = OUT; ctx.fill();
          ell(-0.055, -0.08, 0.065, 0.072); ctx.fillStyle = FILL; ctx.fill();
          ell(0.06, 0.08, 0.03, 0.034); ctx.fill();
          ctx.globalAlpha = 1;
        });
      });
      // Schnauze mit Nasenlöchern (an der Seite ragt sie leicht über den Kopfrand)
      onSphere(0, -0.14, 0.025, function (al) {
        ctx.globalAlpha = al;
        ell(0, 0, 0.17, 0.105); ctx.fillStyle = pal.skin; ctx.fill(); ctx.strokeStyle = OUT; ctx.stroke();
        ctx.fillStyle = OUT; ell(-0.05, -0.005, 0.02, 0.014); ctx.fill(); ell(0.05, -0.005, 0.02, 0.014); ctx.fill();
        ctx.globalAlpha = 1;
      });
      // Mund: offenes Lächeln mit Zunge
      onSphere(0, -0.58, 0.01, function (al) {
        ctx.globalAlpha = al;
        ctx.beginPath(); ctx.moveTo(-0.32, -0.07); ctx.quadraticCurveTo(0, 0.06, 0.32, -0.07);
        ctx.quadraticCurveTo(0.24, 0.36, 0, 0.38); ctx.quadraticCurveTo(-0.24, 0.36, -0.32, -0.07); ctx.closePath();
        ctx.fillStyle = OUT; ctx.fill(); ctx.strokeStyle = OUT; ctx.stroke();
        ctx.beginPath(); ctx.ellipse(0, 0.29, 0.15, 0.09, 0, Math.PI, 0, true); ctx.fillStyle = pal.tongue; ctx.fill();
        ctx.globalAlpha = 1;
      });
    });

    // ------------------------------------------------ Arme (Ärmel + Faust)
    // Faust: geschlossen, vier eingerollte Finger am Ende, Daumen quer darüber. Immer zu, nie offen.
    function fist(fc, dirx, diry, side) {
      var ux = dirx, uy = diry, px = -uy * side, py = ux * side;     // u = Richtung des Unterarms, p = quer dazu
      function at(u, p) { return [fc[0] + ux * u * S + px * p * S, fc[1] + uy * u * S + py * p * S]; }
      function blob(u, p, r) { var c = at(u, p); ctx.beginPath(); ctx.arc(c[0], c[1], r * S, 0, Math.PI * 2); }
      var lw = OL * 0.95;
      // Umriss: Handrücken plus vier Fingerglieder (Kontur zuerst, Füllung danach -> eine Silhouette)
      var FP = [-0.030, -0.010, 0.010, 0.030];
      ctx.fillStyle = OUT; ctx.strokeStyle = OUT; ctx.lineWidth = 2 * OL * 0.95;
      blob(-0.004, 0, 0.052); ctx.stroke(); ctx.fill();
      FP.forEach(function (p) { blob(0.032, p, 0.0195); ctx.stroke(); ctx.fill(); });
      ctx.fillStyle = pal.skin;
      blob(-0.004, 0, 0.052); ctx.fill();
      FP.forEach(function (p) { blob(0.032, p, 0.0195); ctx.fill(); });
      // Trennlinien zwischen den Fingern und die Falte, in der die Finger einrollen
      ctx.strokeStyle = OUT; ctx.lineWidth = OL * 0.6;
      for (var k = 0; k < 3; k++) { var m = (FP[k] + FP[k + 1]) / 2; seg(at(0.020, m), at(0.046, m)); }
      ctx.beginPath(); var c0 = at(0.018, FP[0] - 0.016); ctx.moveTo(c0[0], c0[1]);
      var c1 = at(0.012, 0), c2 = at(0.018, FP[3] + 0.016); ctx.quadraticCurveTo(c1[0], c1[1], c2[0], c2[1]); ctx.stroke();
      // Daumen: liegt quer über den Fingern
      var th = at(0.006, -0.024);
      ctx.save(); ctx.translate(th[0], th[1]); ctx.rotate(Math.atan2(py, px));
      ctx.beginPath(); ctx.ellipse(0, 0, 0.030 * S, 0.0185 * S, 0, 0, Math.PI * 2);
      ctx.fillStyle = pal.skin; ctx.fill(); ctx.strokeStyle = OUT; ctx.lineWidth = OL * 0.8; ctx.stroke();
      ctx.restore();
    }

    function arm(sh, el, wr, side) {
      var z = (el[2] + wr[2]) / 2;
      var s0 = P(sh), s1 = P(el), s2 = P(wr);
      part(z, function () {
        tube([s0, s1, s2], [S * 0.092, S * 0.082], pal.gi);
        cross2(s1, s2, 0.80, S * 0.040, pal.giLine);
      });
      var dir = norm(sub(wr, el)), fc = P(add(wr, mul(dir, 0.030)));
      part(Math.min(z, wr[2]) - 0.01, function () {
        var dd = [s2[0] - s1[0], s2[1] - s1[1]], l = Math.hypot(dd[0], dd[1]);
        // zeigt der Unterarm zur Kamera, bleibt die letzte sinnvolle Richtung: nach außen zum Körperrand
        var ux = l > S * 0.02 ? dd[0] / l : 0, uy = l > S * 0.02 ? dd[1] / l : -1;
        fist(fc, ux, uy, side);
      });
    }
    arm(f.Ls, f.Le, f.Lw, 1); arm(f.Rs, f.Re, f.Rw, -1);

    // ------------------------------------------------ Beine (Hose + Fuß)
    function leg(hp, kn, an, heel, toe) {
      var z = (kn[2] + an[2]) / 2 + 0.06;
      var h0 = P(hp), k0 = P(kn), a0 = P(an), he = P(heel), to = P(toe);
      part(z, function () {
        tube([he, to], [S * 0.078], pal.skin);
        var dd = sub(to, he), l = Math.hypot(dd[0], dd[1]) || 1, ux = dd[0] / l, uy = dd[1] / l;
        ctx.lineWidth = OL * 0.7; ctx.strokeStyle = OUT;        // Zehen
        for (var k = 0; k < 2; k++) {
          var px = -uy, py = ux, bx = to[0] - (to[0] - he[0]) * 0.0 + ux * 0, by = 0;
          var cx = lerp(he[0], to[0], 0.78) + px * (k ? 1 : -1) * S * 0.010, cy = lerp(he[1], to[1], 0.78) + py * (k ? 1 : -1) * S * 0.010;
          seg([cx + ux * S * 0.004, cy + uy * S * 0.004], [cx + ux * S * 0.044, cy + uy * S * 0.044]);
        }
        tube([h0, k0, a0], [S * 0.128, S * 0.112], pal.gi);
        cross2(k0, a0, 0.80, S * 0.052, pal.giLine);
      });
    }
    leg(f.Lh, f.Lk, f.La, f.Lhl, f.Lt); leg(f.Rh, f.Rk, f.Ra, f.Rhl, f.Rt);

    // ------------------------------------------------ Stab
    var s0 = P(f.S0), s1 = P(f.S1);
    var holdZ = mode === 'B' ? Math.max(f.Lw[2], f.Rw[2]) : (mode === 'L' ? f.Lw[2] : f.Rw[2]);
    part(holdZ + 0.002, function () {
      // Schwung-Spur aus den Vor-Frames
      var trail = opt.trail == null ? 4 : opt.trail;
      for (var k = trail; k >= 1; k--) {
        var pr = unpack(d, rowAt(d, t - k / d.fps / 1.0 * 1).row), pn = unpack(d, rowAt(d, t - (k - 1) / d.fps).row);
        var A0 = P(pr.S0), A1 = P(pr.S1), B0 = P(pn.S0), B1 = P(pn.S1);
        var ang = Math.abs(Math.atan2(A1[1] - A0[1], A1[0] - A0[0]) - Math.atan2(B1[1] - B0[1], B1[0] - B0[0]));
        if (ang > Math.PI) ang = 2 * Math.PI - ang;
        if (ang > 1.3) continue;
        ctx.fillStyle = 'rgba(20,20,20,' + (0.05 + 0.02 * (trail - k)).toFixed(3) + ')';
        ctx.beginPath(); ctx.moveTo(A0[0], A0[1]); ctx.lineTo(A1[0], A1[1]); ctx.lineTo(B1[0], B1[1]); ctx.lineTo(B0[0], B0[1]); ctx.closePath(); ctx.fill();
      }
      tube([s0, s1], [S * 0.024], pal.staff);
      var dx = s1[0] - s0[0], dy = s1[1] - s0[1], l = Math.hypot(dx, dy) || 1, ux = dx / l, uy = dy / l;
      ctx.strokeStyle = OUT; ctx.lineWidth = S * 0.024;
      seg(s0, [s0[0] + ux * S * 0.05, s0[1] + uy * S * 0.05]);
      seg(s1, [s1[0] - ux * S * 0.05, s1[1] - uy * S * 0.05]);
    });

    // ------------------------------------------------ sortieren und zeichnen (weit weg zuerst)
    parts.sort(function (a, b) { return b.z - a.z; });
    parts.forEach(function (p) { ctx.save(); p.fn(); ctx.restore(); });
    ctx.restore();
  }

  // Tiefe der tiefsten Sohle unter dem Becken (für den Schatten)
  function soleDepth(f) {
    return Math.max(f.La[1], f.Ra[1], f.Lhl[1], f.Rhl[1], f.Lt[1], f.Rt[1]) + 0.03;
  }

  global.Momo = { load: load, draw: draw };
})(window);
