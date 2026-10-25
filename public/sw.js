// Service worker de Rasante: la web sigue funcionando sin cobertura con lo ya visitado y lo guardado.
// - Páginas: red primero (con 5 s de margen) y, si no hay, la copia guardada o la página «sin conexión».
// - Ficheros de la web (/_next/static, inmutables): caché primero.
// - Teselas del mapa y fotos: caché primero, con tope de entradas (solo lo que el usuario ha visto).
// - «Guardar para sin conexión»: la página va a una caché aparte que no se recorta.
const VERSION = "v2";
const PAGINAS = `paginas-${VERSION}`;
const GUARDADAS = "guardadas";
const ESTATICOS = `estaticos-${VERSION}`;
const TESELAS = "teselas";
const FOTOS = "fotos";
const SIN_CONEXION = "/sin-conexion";
const TOPES = { [PAGINAS]: 60, [TESELAS]: 1500, [FOTOS]: 150 };

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(PAGINAS).then((c) => c.addAll([SIN_CONEXION, "/"])).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  const vigentes = new Set([PAGINAS, GUARDADAS, ESTATICOS, TESELAS, FOTOS]);
  e.waitUntil(
    caches
      .keys()
      .then((ks) => Promise.all(ks.filter((k) => !vigentes.has(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

async function recortar(nombre) {
  const tope = TOPES[nombre];
  if (!tope) return;
  const c = await caches.open(nombre);
  const ks = await c.keys();
  for (const k of ks.slice(0, Math.max(0, ks.length - tope))) await c.delete(k);
}

async function guardarEn(nombre, peticion, respuesta) {
  if (!respuesta || !(respuesta.ok || respuesta.type === "opaque")) return;
  const c = await caches.open(nombre);
  await c.put(peticion, respuesta);
  await recortar(nombre);
}

function conTiempo(promesa, ms) {
  return Promise.race([promesa, new Promise((_, no) => setTimeout(() => no(new Error("tiempo")), ms))]);
}

async function pagina(peticion) {
  const url = new URL(peticion.url);
  const clave = url.pathname + url.search;
  try {
    const r = await conTiempo(fetch(peticion), 5000);
    if (r.ok) {
      // las copias se sacan antes de devolver la respuesta (después el cuerpo ya se habrá leído)
      const copia = r.clone();
      const paraGuardadas = r.clone();
      guardarEn(PAGINAS, clave, copia);
      // si está guardada, se actualiza también la copia guardada
      caches.open(GUARDADAS).then(async (c) => (await c.match(clave)) && c.put(clave, paraGuardadas));
    }
    return r;
  } catch {
    const copia =
      (await caches.match(clave, { cacheName: GUARDADAS })) || (await caches.match(clave, { cacheName: PAGINAS }));
    if (copia) return copia;
    // la página «sin conexión» con su propia dirección (no con la pedida): si React hidrata con otra URL, el
    // enrutador de Next intenta cargar esa ruta sin red y muestra un error
    if (url.pathname === SIN_CONEXION) return caches.match(SIN_CONEXION);
    return Response.redirect(SIN_CONEXION, 302);
  }
}

async function cachePrimero(nombre, peticion) {
  const guardada = await caches.match(peticion, { cacheName: nombre });
  if (guardada) return guardada;
  const r = await fetch(peticion);
  guardarEn(nombre, peticion, r.clone());
  return r;
}

self.addEventListener("fetch", (e) => {
  const p = e.request;
  if (p.method !== "GET") return;
  const url = new URL(p.url);
  if (p.mode === "navigate" && url.origin === location.origin) return e.respondWith(pagina(p));
  if (url.origin === location.origin && url.pathname.startsWith("/_next/static/"))
    return e.respondWith(cachePrimero(ESTATICOS, p));
  if (url.hostname === "tile.openstreetmap.org") return e.respondWith(cachePrimero(TESELAS, p));
  if (url.hostname === "upload.wikimedia.org") return e.respondWith(cachePrimero(FOTOS, p));
});

// Desde la página: guardar o quitar una página para usarla sin conexión
self.addEventListener("message", (e) => {
  const { tipo, url } = e.data || {};
  if (tipo === "guardar") {
    e.waitUntil(
      fetch(url)
        .then((r) => (r.ok ? caches.open(GUARDADAS).then((c) => c.put(url, r)) : Promise.reject()))
        .then(() => e.source?.postMessage({ tipo: "guardada", url }))
        .catch(() => e.source?.postMessage({ tipo: "error", url })),
    );
  } else if (tipo === "quitar") {
    e.waitUntil(caches.open(GUARDADAS).then((c) => c.delete(url)));
  }
});
