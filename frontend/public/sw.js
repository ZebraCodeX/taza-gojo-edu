/* Taza-Gojo EDU service worker.
 *
 * Strategy that matters on rural 2G/3G:
 *   - App shell:  Cache-First  (app boots without a network round trip)
 *   - API GETs:   Network-First, falling back to the cached reply (so a lesson
 *                 you already visited keeps working when the mast drops out)
 *   - Definitions are tiny JSON that can be flushed to a flash drive / mesh AP
 *                 and pre-seeded into the cache (see docs/offline-first.md).
 */

const SHELL_CACHE = "tazagojo-shell-v2";
const DATA_CACHE = "tazagojo-data-v1";
const SHELL_ASSETS = ["/", "/index.html", "/manifest.webmanifest", "/icons/icon.svg", "/icons/icon-192.png", "/icons/icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(SHELL_CACHE).then((c) => c.addAll(SHELL_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== SHELL_CACHE && k !== DATA_CACHE).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // API lives on the backend origin in prod;
  // the dev proxy keeps everything same-origin so this is safe to cache.

  const isApi = url.pathname.startsWith("/api/");
  const isShell = url.pathname === "/" || url.pathname.startsWith("/assets/") || SHELL_ASSETS.includes(url.pathname);

  if (isShell) {
    e.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(SHELL_CACHE).then((c) => c.put(req, copy));
        return res;
      }))
    );
    return;
  }

  if (isApi) {
    e.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(DATA_CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => caches.match(req).then((hit) => hit || Response.error()))
    );
  }
});

// Background Sync: flush the offline queue when the OS lets us sync.
self.addEventListener("sync", (e) => {
  if (e.tag === "tazagojo-sync") {
    e.waitUntil(
      self.clients.matchAll().then((clients) =>
        clients.forEach((c) => c.postMessage({ type: "TAZAGOJO_FLUSH_QUEUE" }))
      )
    );
  }
});