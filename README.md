# sgrdg-live
Live-Daten und FUSSBALL.DE-Widgets für die SG RDG App

## Foto-Muster (`/fotomuster/`)

App, die neue Fotos unverändert in Muster für Mo, Di, Mi, Do, Fr, Sa und Event einsetzt.
Läuft komplett im Browser bzw. als installierte App – es wird nichts hochgeladen.

**Auf dem Android-Handy installieren:** `…/fotomuster/` in Chrome öffnen → Button
„Installieren“ (oder Chrome-Menü ⋮ → „App installieren“ / „Zum Startbildschirm hinzufügen“).
Danach startet sie wie eine normale App und funktioniert auch offline.

- Muster (mit Fotobereich) werden einmal hinterlegt und bleiben auf dem Gerät gespeichert.
- Reihenfolge der neuen Fotos: 1 → Montag … 6 → Samstag, 7 → Event.
- Fotos werden nicht zugeschnitten, gefiltert oder verzerrt, nur proportional in den Fotobereich eingepasst.
- Ausgabe als PNG in der Originalgröße des Musters (einzeln, als ZIP oder per „Teilen“).
- Bei Änderungen an der App die Versionsnummer in `fotomuster/sw.js` (`CACHE`) erhöhen.
