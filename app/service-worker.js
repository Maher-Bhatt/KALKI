const CACHE_NAME = 'kalki-pwa-v1.2.0';
const ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/service-worker.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (url.pathname.includes('/api/') || event.request.mode === 'navigate' || url.pathname === '/' || url.pathname.endsWith('.html')) {
    // Never serve stale API or shell HTML after an update.
    event.respondWith(fetch(event.request));
  } else {
    // Cache first for static assets, falling back to network.
    event.respondWith(
      caches.match(event.request)
        .then((response) => response || fetch(event.request))
    );
  }
});
