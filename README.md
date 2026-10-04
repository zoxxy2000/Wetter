# Wetter-App (PWA) – Installation auf Android

Die App braucht eine HTTPS-Adresse, damit Android sie als App installieren kann
(Standort, Offline-Start und Mitteilungen funktionieren nur über HTTPS).

## Variante A: GitHub Pages (kostenlos, ca. 5 Minuten)
1. Auf github.com ein neues, öffentliches Repository anlegen, z. B. `wetter`.
2. Alle Dateien aus diesem Ordner hochladen („Add file" → „Upload files").
3. Settings → Pages → Branch `main`, Ordner `/ (root)` → Save.
4. Nach ca. 1 Minute ist die App unter `https://DEINNAME.github.io/wetter/` erreichbar.
5. Auf dem Android-Handy in Chrome öffnen → Menü ⋮ → „App installieren"
   (oder „Zum Startbildschirm hinzufügen").

## Variante B: eigener Server (Unraid)
Ordner in einen Webserver-Container legen (z. B. nginx) und über den
vorhandenen Reverse-Proxy mit HTTPS-Zertifikat erreichbar machen.

## Echte APK für den Play Store / zum Weitergeben
Wenn die App per HTTPS läuft: https://www.pwabuilder.com aufrufen, die Adresse
eingeben und unter „Android" ein Paket erzeugen lassen.

## Anpassen
Oben im `<script>` von `index.html` steht der Block `CFG`:
Startort, Pegelstation, Schwellwerte, Aktualisierungsintervall, Radar-Umkreis.
Nach Änderungen in `sw.js` die `VERSION` hochzählen, damit Handys die neue
Fassung laden.
