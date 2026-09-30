#!/usr/bin/env python3
"""Rendert Momos Bewegung (index.html + motion.json) Bild für Bild mit Chromium zu MP4 und GIF.

Aufruf:  python render_video.py [--out ../momo-form.mp4] [--gif ../momo-form.gif] [--size 1080] [--style color|line]
         python render_video.py --stills 0.3 4.3 8.3 --stills-out sheet.png   (nur Stichproben)
Benötigt: playwright (pip), ffmpeg, Chromium (PLAYWRIGHT_BROWSERS_PATH oder --chromium).
"""
import argparse, base64, functools, http.server, json, os, subprocess, threading
from playwright.sync_api import sync_playwright

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)

ap = argparse.ArgumentParser()
ap.add_argument("--out", default=os.path.join(root, "momo-form.mp4"))
ap.add_argument("--gif", default=None)
ap.add_argument("--size", type=int, default=1080)
ap.add_argument("--style", choices=["color", "line"], default="color")
ap.add_argument("--chromium", default=None)
ap.add_argument("--stills", type=float, nargs="*")
ap.add_argument("--stills-out", default="stills.png")
a = ap.parse_args()

Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
Handler.log_message = lambda *args, **kw: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_address[1]}/index.html?still&style={a.style}"

fps = json.load(open(os.path.join(root, "motion.json")))["fps"]
n_frames = len(json.load(open(os.path.join(root, "motion.json")))["frames"])

with sync_playwright() as pw:
    kw = {}
    exe = a.chromium or next((os.path.join(dp, "chrome") for dp, dn, fn in os.walk(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
                              if "chrome" in fn and "headless" not in dp), None)
    if exe:
        kw["executable_path"] = exe
    br = pw.chromium.launch(args=["--no-sandbox"], **kw)
    pg = br.new_page(viewport={"width": 1100, "height": 1300})
    pg.goto(url)
    pg.wait_for_function("window.momoReady === true")
    pg.evaluate(f"(s)=>{{const c=document.getElementById('c'); c.width=s; c.height=s;}}", a.size)

    def shot(t):
        b64 = pg.evaluate("(t)=>{renderAt(t); return document.getElementById('c').toDataURL('image/png').split(',')[1];}", t)
        return base64.b64decode(b64)

    if a.stills:
        import cv2, numpy as np
        tiles = [cv2.imdecode(np.frombuffer(shot(t), np.uint8), cv2.IMREAD_COLOR) for t in a.stills]
        cv2.imwrite(a.stills_out, np.hstack(tiles))
        print("Stichproben:", a.stills_out)
    else:
        ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
                               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", a.out],
                              stdin=subprocess.PIPE)
        for i in range(n_frames):
            ff.stdin.write(shot(i / fps))
        ff.stdin.close(); ff.wait()
        print("Video:", a.out)
        if a.gif:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.out, "-vf",
                            "fps=15,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=48[p];[s1][p]paletteuse=dither=bayer:bayer_scale=4",
                            a.gif], check=True)
            print("GIF:", a.gif)
    br.close()
