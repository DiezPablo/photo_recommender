// La web se ha mudado a https://safarirecommender.vercel.app (spec 017 del repo nuevo). Este service worker
// sustituye al anterior para que no queden páginas viejas sin conexión: borra sus cachés, se da de baja y
// recarga las pestañas abiertas, que ya reciben la redirección.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => {
  e.waitUntil(
    (async () => {
      for (const k of await caches.keys()) await caches.delete(k);
      await self.registration.unregister();
      for (const c of await self.clients.matchAll({ type: "window" })) c.navigate(c.url);
    })(),
  );
});
