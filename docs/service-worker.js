// This file needs to be top-level so that service worker scoping works

const cacheName = "__CACHE_NAME__";
const urlsToCache = ["__URLS_TO_CACHE__"];

// The build step fills in the values above. The dev server copies this file without running that
// step, so an unprocessed worker must remove itself instead of caching the site. Otherwise a
// worker from an earlier build stays in control and keeps serving files from its old cache.
const isUnprocessed = cacheName.includes("CACHE_NAME");

if (isUnprocessed) {
  self.addEventListener('install', () => {
    self.skipWaiting();
  });

  self.addEventListener('activate', event => {
    event.waitUntil(
      caches.keys()
        .then(keys => Promise.all(keys.map(key => caches.delete(key))))
        .then(() => self.registration.unregister())
        .then(() => self.clients.matchAll({ type: 'window' }))
        .then(clients => clients.forEach(client => client.navigate(client.url)))
    );
  });
} else {
  // Install and cache resources.
  // "reload" skips the HTTP cache, which could still have pages from the previous build.
  // Those pages would link to hashed assets that are not in this build's cache.
  self.addEventListener('install', event => {
    self.skipWaiting();
    event.waitUntil(
      caches.open(cacheName)
        .then(cache => cache.addAll(urlsToCache.map(url => new Request(url, { cache: 'reload' }))))
    );
  });

  // Fetch from cache, fallback to network
  self.addEventListener('fetch', event => {
    const request = event.request;
    if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) return;

    event.respondWith(respond(request));
  });

  const respond = async request => {
    // Search results link to pages with a "?h=" query that highlights the search term.
    // The cached pages have no query, so the query is ignored when matching.
    const cached = await caches.match(request, { ignoreSearch: true });
    if (cached) return cached;

    try {
      return await fetch(request);
    } catch (error) {
      if (request.mode !== 'navigate') throw error;
      return offlinePage(request);
    }
  };

  const offlinePage = async request => {
    // Page URLs end with a slash. The server redirects to it, but cannot do so while offline.
    const url = new URL(request.url);
    url.search = '';
    if (!url.pathname.endsWith('/')) {
      url.pathname += '/';
      if (await caches.match(url.href)) return Response.redirect(url.href, 301);
    }

    // The 404 page uses absolute links, so it works from any URL.
    const notFound = await caches.match(new URL('404.html', self.registration.scope).href);
    if (notFound) return new Response(notFound.body, { status: 404, headers: notFound.headers });
    return Response.error();
  };

  // Clean old caches when new service worker is installed
  self.addEventListener('activate', event => {
    clients.claim();
    const cacheWhitelist = [cacheName];
    event.waitUntil(
      caches.keys()
        .then(keys => Promise.all(
          keys.map(key => {
            if (!cacheWhitelist.includes(key)) {
              return caches.delete(key);
            }
          })
        ))
    );
  });
}
