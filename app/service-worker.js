/* KALKI service worker.
 *
 * The previous version was cache-first for every non-API, non-HTML request
 * (`caches.match(req) || fetch(req)`), which meant a shipped frontend asset
 * was cached forever and application updates could never reach a user. With a
 * multi-file frontend that is a release-blocking bug, so the policy is now:
 *
 *   /api/*, navigations, HTML  → network only        (never stale)
 *   /ui/*  (app code)          → network-first       (update lands immediately,
 *                                                     cache is an offline fallback)
 *   everything else (assets)   → stale-while-revalidate
 *
 * CACHE_VERSION is bumped with the app version by the release pipeline; the
 * activate handler deletes every cache that does not match, so an upgrade
 * cannot leave a previous build's JavaScript behind.
 */

const CACHE_VERSION = 'v2.0.0';
const CACHE_NAME = `kalki-${CACHE_VERSION}`;

const PRECACHE = ['/', '/index.html', '/manifest.json'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE).catch(() => undefined))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('message', (event) => {
  if (event.data === 'skip-waiting') self.skipWaiting();
});

async function networkFirst(request) {
  try {
    const fresh = await fetch(request);
    if (fresh && fresh.ok && request.method === 'GET') {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, fresh.clone());
    }
    return fresh;
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) return cached;
    throw err;
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const network = fetch(request)
    .then((res) => { if (res && res.ok) cache.put(request, res.clone()); return res; })
    .catch(() => undefined);
  return cached || network || fetch(request);
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Never serve API responses or the shell from cache.
  if (url.pathname.startsWith('/api/') || request.mode === 'navigate' ||
      url.pathname === '/' || url.pathname.endsWith('.html')) {
    event.respondWith(fetch(request));
    return;
  }

  // Application code: always try the network so updates land at once.
  if (url.pathname.startsWith('/ui/') || url.pathname === '/service-worker.js') {
    event.respondWith(networkFirst(request));
    return;
  }

  event.respondWith(staleWhileRevalidate(request));
});
