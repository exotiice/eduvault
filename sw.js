/* EduVault : fonctionne hors-ligne + notifie quand une nouvelle version est prete. */
const C = 'eduvault-v35';
const CDN = ['cdnjs.cloudflare.com', 'fonts.googleapis.com', 'fonts.gstatic.com'];
const PRE = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png', 'icon-shortcut-quiz.png', 'icon-shortcut-focus.png', 'icon-shortcut-cards.png', 'icon-shortcut-agenda.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(C).then(c => Promise.all(PRE.map(u => fetch(new Request(u, { cache: 'reload' })).then(r => r.ok && c.put(u, r)).catch(() => {})))));
  /* pas de self.skipWaiting() ici : on laisse la nouvelle version "attendre"
     pour pouvoir prevenir la personne avant de l'activer (voir index.html) */
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== C).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('message', e => {
  if (e.data && e.data.type === 'SKIP_WAITING') self.skipWaiting();
});

/* « Partager vers EduVault » (Web Share Target) : les fichiers reçus sont gardés dans un cache dédié, l'appli les propose ensuite à l'import */
async function shareTarget(r) {
  try {
    const fd = await r.formData(), c = await caches.open('eduvault-share'), t = Date.now();
    let n = 0;
    for (const f of fd.getAll('files')) {
      if (!f || !f.size) continue;
      await c.put(new Request('shared/' + t + '-' + (n++)), new Response(f, { headers: { 'Content-Type': f.type || 'application/octet-stream', 'X-Name': encodeURIComponent(f.name || 'fichier') } }));
    }
    const meta = { title: fd.get('title') || '', text: fd.get('text') || '', url: fd.get('url') || '' };
    if (meta.title || meta.text || meta.url) await c.put(new Request('shared/' + t + '-t'), new Response(JSON.stringify(meta), { headers: { 'Content-Type': 'application/json', 'X-Kind': 'text' } }));
  } catch (x) {}
  return Response.redirect(new URL('./?share=1', self.registration.scope).href, 303);
}

self.addEventListener('fetch', e => {
  const r = e.request;
  if (r.method === 'POST' && new URL(r.url).pathname.endsWith('/share-target')) { e.respondWith(shareTarget(r)); return; }
  if (r.method !== 'GET') return;
  const u = new URL(r.url);
  /* bibliothèques (KaTeX, highlight.js) et polices : mises en cache au premier chargement pour le hors-ligne */
  if (CDN.includes(u.hostname)) {
    e.respondWith(caches.match(r).then(m => m || fetch(r).then(res => { if (res.ok || res.type === 'opaque') { const cp = res.clone(); caches.open(C).then(c => c.put(r, cp)); } return res; })));
    return;
  }
  if (u.origin !== location.origin) return;
  /* page, icônes, manifeste : on affiche tout de suite la copie en cache, et on la met à jour en arrière-plan (ouverture instantanée) */
  if (r.mode === 'navigate' || /\.(html|png|svg|ico|webmanifest|woff2?)$/i.test(u.pathname) || u.pathname.endsWith('/')) {
    e.respondWith(caches.match(r, { ignoreSearch: true }).then(m => {
      const net = fetch(r, r.mode === 'navigate' ? { cache: 'no-cache' } : undefined).then(res => {
        if (res && res.ok && res.type === 'basic') { const cp = res.clone(); caches.open(C).then(c => c.put(r, cp)); }
        return res;
      });
      if (m) { net.catch(() => {}); return m; }
      return net.catch(() => caches.match('index.html'));
    }));
    return;
  }
  e.respondWith(
    fetch(r).then(res => { if (res.ok) { const cp = res.clone(); caches.open(C).then(c => c.put(r, cp)); } return res; })
      .catch(() => caches.match(r, { ignoreSearch: true }).then(m => m || caches.match('index.html')))
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

/* notifications push (Firebase Cloud Messaging / Web Push) : affichées même application fermée */
self.addEventListener('push', e => {
  let p = {};
  try { p = e.data ? e.data.json() : {}; } catch (x) { try { p = { notification: { body: e.data.text() } }; } catch (y) {} }
  const n = p.notification || p.data || {}, d = p.data || {};
  e.waitUntil(self.registration.showNotification(n.title || 'EduVault', {
    body: n.body || '', icon: 'icon-192.png', badge: 'icon-192.png', tag: d.tag || 'eduvault-announce', data: { url: d.url || './' }
  }));
});
