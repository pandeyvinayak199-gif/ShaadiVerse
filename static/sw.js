const CACHE='shaadi-shell-v4';
const SHELL=['/','/style.css','/app.js','/features.js','/pilot.js','/palace.svg','/vendor/jsQR.js'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)));self.skipWaiting()});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener('fetch',event=>{
 const url=new URL(event.request.url);
 // Never cache authenticated API responses, passes, guest information or provider responses.
 if(event.request.method!=='GET'||url.origin!==location.origin||url.pathname.startsWith('/api/'))return;
 if(event.request.mode==='navigate'){event.respondWith(fetch(event.request).catch(()=>caches.match('/')));return}
 if(SHELL.includes(url.pathname))event.respondWith(fetch(event.request).then(response=>{if(response.ok){const copy=response.clone();caches.open(CACHE).then(c=>c.put(event.request,copy))}return response}).catch(()=>caches.match(event.request)));
});
