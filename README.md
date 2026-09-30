# sgrdg-live
Live-Daten und FUSSBALL.DE-Widgets für die SG RDG App

## CAM AGENT (`/fotomuster/`)

App für die Tages-Layouts von Black-Box Sports Academy (Mo, Di, Mi, Do, Fr, Sa und Event):
Das Layout bleibt bestehen, nur das Foto rechts wird durch ein neues ersetzt – passend
zugeschnitten und in Schwarz-Weiß. Läuft komplett im Browser bzw. als installierte App,
es wird nichts hochgeladen.

**Auf dem Android-Handy installieren:** `…/fotomuster/` in Chrome öffnen → Button
„Installieren“ (oder Chrome-Menü ⋮ → „App installieren“ / „Zum Startbildschirm hinzufügen“).
Danach startet sie wie eine normale App und funktioniert auch offline.

- Muster (Tages-Layout) einmal hochladen; der Fotobereich wird automatisch erkannt
  (Textfeld links + Foto rechts, oder durchsichtiges Fenster in einem PNG) und bleibt auf dem Gerät gespeichert.
- Reihenfolge der neuen Fotos: 1 → Montag … 6 → Samstag, 7 → Event; pro Bild änderbar.
- Standard: Foto füllt den Fotobereich (zugeschnitten) und ist Schwarz-Weiß.
  Der Ausschnitt lässt sich pro Foto verschieben. Optional: „Ganz“ (ganzes Foto zeigen) und „Farbe“.
- Alles außerhalb des Fotobereichs bleibt Pixel für Pixel unverändert.
- Der weiße Rand des Musters bleibt rundherum erhalten, auch um das neue Foto. Ragt ein Fotobereich
  in den Rand hinein, wird er automatisch verkleinert (auch bei älteren gespeicherten Mustern).
- Ausgabe als PNG in der Originalgröße des Musters (einzeln, als ZIP oder per „Teilen“).
- Bei Änderungen an der App die Versionsnummer in `fotomuster/sw.js` (`CACHE`) erhöhen.
- Schriften (Anton, Inter, IBM Plex Mono; SIL Open Font License) liegen in `fotomuster/fonts/`.

## Momo läuft die Form (`/momo/`)

Momo (Schildkröte, Farben nach der farbigen Momo-Vorlage) läuft die Form (CFW, Form mit Waffe) von Max. Die Hände sind
von Anfang bis Ende zur Faust geschlossen. Die Bewegung stammt aus einem
Video; im Endergebnis ist nur Momo zu sehen, kein Bildmaterial aus dem Video.

- `momo/index.html` – Player (Abspielen, Zeitleiste, Tempo), läuft im Browser aus `motion.json`.
- `momo/momo-form.mp4` (1080×1080, 29,97 fps, ohne Ton) und `momo/momo-form.gif` – fertige Ausgabe.
- `momo/momo.js` – Momo als Figur aus Einzelteilen (Kopf, Gi, Gürtel, Arme, Beine, Panzer, Stab); dreht sich
  von vorn über die Seite zum Rücken.
  Der Strichstil (schwarz-weiß) bleibt als Option: `index.html?style=line` bzw. `render_video.py --style line`.
- `momo/motion.json` – die übertragene Bewegung (Momos Proportionen, 3D-Gelenke pro Bild).

So entsteht es (in `momo/tools/`, Python mit `mediapipe`, `opencv-python-headless`, `scipy`, `playwright`, `ffmpeg`):

1. `extract_pose.py VIDEO.mp4 pose_raw.json` liest mit MediaPipe (Pose Landmarker „heavy“, Modelldatei
   `pose_heavy.task` neben das Skript legen) die Körperpose. Die Ergebnisse dieses Videos liegen als
   `pose_raw.json.gz` im Ordner.
2. `make_motion.py pose_raw.json.gz ../motion.json --staff staff_keys.json` überträgt die Knochenrichtungen auf
   Momos Proportionen (Arme mit den Winkeln aus dem Bild, Beine und Rumpf aus der 3D-Schätzung).
3. `render_video.py --gif ../momo-form.gif` rendert `index.html` Bild für Bild mit Chromium zu MP4 und GIF.

Der Stab steckt nicht in der Pose. `staff_keys.json` wurde deshalb von Hand aus dem Video abgelesen (alle 0,25 s:
welche Hand hält ihn, wie liegt er in der Bildebene) und wird dazwischen interpoliert. Er ist daher ungenauer als
der Körper, besonders bei schnellen Wirbeln.

### Momo mit Fäusten (`/momo/faust/`)

`momo/faust/momo-faust.mp4` ist das farbige Momo-Video (1920×1088, 30 fps, mit Originalton), in dem von Anfang bis
Ende beide Hände zur Faust geballt sind. Der Rest des Videos ist unverändert.

- `detect_hands.py` findet in jedem Bild die Hände (grüne Hautflächen ohne Kopf, Füße und Panzer).
- `make_fists.py` entfernt die alte Hand (Füllung mit den Nachbarfarben) und zeichnet an ihre Stelle eine Faust im
  Stil der Vorlage (vier eingerollte Finger, Daumen quer darüber). Positionen und Richtung werden über die Zeit geglättet.
- `manual.json`: Faustpositionen, die von Hand aus dem Video abgelesen wurden, wo sich Hände per Farbe nicht finden
  lassen (Hand auf dem Gesicht bei ca. 11,6–12,3 s, verzerrte Bilder bei ca. 13,5–13,8 s).

```
MOMO_SRC=momo-original.mp4 python detect_hands.py
MOMO_SRC=momo-original.mp4 python make_fists.py video momo-faust.mp4
```

Grenzen: Das Ausgangsvideo hat einzelne verzerrte Bilder (z. B. bei 12,25 s). Dort sind die Fäuste frei eingesetzt und
der Hintergrund darum herum bleibt leicht unsauber. Hände, die im Video hinter dem Körper verschwinden (Rückenansicht),
bleiben verdeckt.
