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
