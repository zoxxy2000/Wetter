# Wetter-App (PWA) – Installation auf Android

Die App braucht eine HTTPS-Adresse, damit Android sie als App installieren kann
(Standort, Offline-Start und Mitteilungen funktionieren nur über HTTPS).

## Echte APK für den Play Store / zum Weitergeben
Wenn die App per HTTPS läuft: https://www.pwabuilder.com aufrufen, die Adresse
eingeben und unter „Android" ein Paket erzeugen lassen.

## Anpassen
Oben im `<script>` von `index.html` steht der Block `CFG`:
Startort, Pegelstation, Schwellwerte, Aktualisierungsintervall, Radar-Umkreis.
Nach Änderungen in `sw.js` die `VERSION` hochzählen, damit Handys die neue
Fassung laden.
