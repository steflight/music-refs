/* Music Refs — service worker : cache shell + Web Push (MR-08 rappel quotidien, MR-14 défi). */
const CACHE = 'music-refs-v15';
const SHELL = ['/daily.html', '/', '/party.html'];
const ICON = '/icons/icon-192.png';
const BADGE = '/icons/badge-96.png';

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL).catch(() => undefined)),
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/api/')) return;
  event.respondWith(
    fetch(event.request)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(event.request, copy)).catch(() => undefined);
        return res;
      })
      .catch(() => caches.match(event.request)),
  );
});

/* ---- Web Push ---------------------------------------------------------- */

function parsePayload(event) {
  const fallback = { title: 'Music Refs', body: 'Les refs du jour t’attendent.', url: '/daily.html?ref=push' };
  if (!event.data) return fallback;
  try {
    const data = event.data.json();
    return { ...fallback, ...(data && typeof data === 'object' ? data : {}) };
  } catch (_) {
    try { return { ...fallback, body: event.data.text() }; } catch (_e) { return fallback; }
  }
}

self.addEventListener('push', (event) => {
  const p = parsePayload(event);
  const options = {
    body: p.body,
    icon: p.icon || ICON,
    badge: p.badge || BADGE,
    tag: p.tag || 'music-refs',
    renotify: !!p.tag,
    lang: 'fr',
    data: { url: p.url || '/daily.html?ref=push' },
  };
  event.waitUntil(self.registration.showNotification(p.title || 'Music Refs', options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = new URL((event.notification.data && event.notification.data.url) || '/daily.html?ref=push', self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((wins) => {
      const same = wins.find((w) => new URL(w.url).origin === self.location.origin);
      if (same) {
        if ('navigate' in same) return same.navigate(target).then((w) => (w || same).focus());
        return same.focus();
      }
      return self.clients.openWindow(target);
    }),
  );
});
