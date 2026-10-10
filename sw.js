/* EduVault : fonctionne hors-ligne + notifie quand une nouvelle version est prete. */
const C = 'eduvault-v11';
const PRE = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(C).then(c => c.addAll(PRE).catch(() => {})));
  /* pas de self.skipWaiting() ici : on laisse la nouvelle version "attendre"
     pour pouvoir prevenir la personne avant de l'activer (voir index.html) */
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('message', e => {
  if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting();
});

self.addEventListener('fetch', e => {
  const r = e.request;
  if (r.method !== 'GET' || new URL(r.url).origin !== location.origin) return;
  e.respondWith(
    fetch(r).then(res => { if (res.ok) { const cp = res.clone(); caches.open(C).then(c => c.put(r, cp)); } return res; })
      .catch(() => caches.match(r).then(m => m || caches.match('index.html')))
  );
});

/* notification avec bouton "Terminé" : clic -> on previent la page ouverte */
self.addEventListener('notificationclick', e => {
  e.notification.close();
  if (e.action === 'done' && e.notification.data && e.notification.data.taskId) {
    e.waitUntil(
      self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(cs => {
        if (cs.length) cs.forEach(c => c.postMessage({ type: 'TASK_DONE', id: e.notification.data.taskId }));
      })
    );
  } else {
    e.waitUntil(
      self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(cs => {
        if (cs.length) return cs[0].focus();
        return self.clients.openWindow('./');
      })
    );
  }
});
