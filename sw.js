// Service Worker: App-Hülle offline verfügbar, Karte & Schrift zwischenspeichern.
const VERSION = "wetter-v2";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon-192.png", "icon-512.png"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  // Seite selbst: erst Netz, sonst Cache
  if (e.request.mode === "navigate") {
    e.respondWith(fetch(e.request).then(r => { caches.open(VERSION).then(c => c.put("index.html", r.clone())); return r; })
      .catch(() => caches.match("index.html")));
    return;
  }
  // Leaflet, Schriften, Kartenkacheln: Cache zuerst, im Hintergrund erneuern
  if (/cdnjs\.cloudflare\.com|fonts\.(googleapis|gstatic)\.com|basemaps\.cartocdn\.com/.test(u.host)) {
    e.respondWith(caches.open(VERSION + "-ext").then(async c => {
      const hit = await c.match(e.request);
      const net = fetch(e.request).then(r => { if (r.ok || r.type === "opaque") c.put(e.request, r.clone()); return r; }).catch(() => hit);
      return hit || net;
    }));
    return;
  }
  if (u.origin === location.origin) e.respondWith(caches.match(e.request).then(h => h || fetch(e.request)));
  // Wetter-APIs laufen ungecacht durch – die App hält den letzten Stand selbst vor.
});
self.addEventListener("notificationclick", e => {
  e.notification.close();
  e.waitUntil(self.clients.matchAll({ type: "window" }).then(cs => cs.length ? cs[0].focus() : self.clients.openWindow("./")));
});
