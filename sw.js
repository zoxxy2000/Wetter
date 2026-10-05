// Service Worker: App-Hülle offline verfügbar, Karte & Schrift zwischenspeichern.
importScripts("version.js");   // Versionsnummer nur in version.js ändern
const VERSION = "wetter-" + self.APP_VERSION;
const KONFIG_CACHE = "pw-konfig";   // merkt sich die Adresse des Push-Servers
const SHELL = ["./", "index.html", "version.js", "manifest.webmanifest", "icon-192.png", "icon-512.png", "badge-96.png",
  "icons/clear-day.svg", "icons/clear-night.svg", "icons/cloudy.svg", "icons/drizzle.svg", "icons/fog-day.svg", "icons/fog-night.svg", "icons/fog.svg", "icons/hail.svg", "icons/overcast-day.svg", "icons/overcast-night.svg", "icons/overcast.svg", "icons/partly-cloudy-day-rain.svg", "icons/partly-cloudy-day-snow.svg", "icons/partly-cloudy-day.svg", "icons/partly-cloudy-night-rain.svg", "icons/partly-cloudy-night-snow.svg", "icons/partly-cloudy-night.svg", "icons/rain.svg", "icons/raindrop.svg", "icons/sleet.svg", "icons/snow.svg", "icons/sunrise.svg", "icons/sunset.svg", "icons/thunderstorms-day-rain.svg", "icons/thunderstorms-night-rain.svg", "icons/thunderstorms-rain.svg", "icons/wind.svg"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSION && k !== KONFIG_CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
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
  if (/cdnjs\.cloudflare\.com|fonts\.(googleapis|gstatic)\.com|basemaps\.cartocdn\.com|tile\.openstreetmap\.org/.test(u.host)) {
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
/* ---------------- Push-Benachrichtigungen ---------------- */
self.addEventListener("message", e => {
  if (e.data?.typ === "pushServer" && e.data.url) e.waitUntil(caches.open(KONFIG_CACHE).then(c => c.put("push-server", new Response(e.data.url))));
});
self.addEventListener("push", e => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch { d = { body: e.data ? e.data.text() : "" }; }
  // iOS verlangt, dass jeder Push sichtbar angezeigt wird – darum immer eine Benachrichtigung zeigen
  e.waitUntil(self.registration.showNotification(d.title || "PW-Wetter", {
    body: d.body || "", tag: d.tag || undefined, renotify: !!d.tag, icon: "icon-192.png", badge: "badge-96.png",
    data: { url: d.url || "./" }, timestamp: Date.now()
  }));
});
self.addEventListener("notificationclick", e => {
  e.notification.close();
  const ziel = new URL(e.notification.data?.url || "./", self.registration.scope);
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(cs => {
    const offen = cs.find(c => c.url.startsWith(self.registration.scope));
    if (offen) { offen.postMessage({ typ: "oeffnen", hash: ziel.hash }); return offen.focus(); }
    return self.clients.openWindow(ziel.href);
  }));
});
self.addEventListener("pushsubscriptionchange", e => {
  // Der Browser hat das Abo erneuert: neues Abo beim Server eintragen
  e.waitUntil((async () => {
    const r = await (await caches.open(KONFIG_CACHE)).match("push-server"); if (!r) return;
    const server = await r.text();
    const { schluessel } = await (await fetch(server, { cache: "no-store" })).json();
    const roh = atob((schluessel + "=".repeat((4 - schluessel.length % 4) % 4)).replace(/-/g, "+").replace(/_/g, "/"));
    const neu = await self.registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: Uint8Array.from(roh, c => c.charCodeAt(0)) });
    await fetch(server, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ aktion: "wechsel", alt: e.oldSubscription?.endpoint || "", abo: neu.toJSON() }) });
  })());
});
