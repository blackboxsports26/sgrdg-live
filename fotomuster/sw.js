/*
   Service Worker: legt die App auf dem Handy ab, damit sie auch ohne Internet startet.
   Wenn sich die App ändert, hier die Versionsnummer erhöhen.
*/

const CACHE = 'camagent-v2';

const ASSETS = [
  './',
  'index.html',
  'manifest.webmanifest',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'icons/icon-maskable-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Aus dem Cache antworten (schnell, offline-fähig) und im Hintergrund aktualisieren.
self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) return;

  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const cached = await cache.match(req, { ignoreSearch:true });
    const refresh = fetch(req).then((res) => {
      if (res.ok) cache.put(req, res.clone());
      return res;
    });

    if (cached){
      event.waitUntil(refresh.catch(() => {}));
      return cached;
    }
    return refresh;
  })());
});
