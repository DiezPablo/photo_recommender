// Páginas guardadas para usar sin conexión: viven en la caché «guardadas» del service worker.
export const CACHE_GUARDADAS = "guardadas";

export async function estaGuardada(url: string): Promise<boolean> {
  if (!("caches" in window)) return false;
  const c = await caches.open(CACHE_GUARDADAS);
  return !!(await c.match(url));
}

/** Pide al service worker que guarde (o quite) la página; resuelve cuando la tiene. */
export function guardar(url: string, quitar = false): Promise<boolean> {
  return new Promise((ok) => {
    const sw = navigator.serviceWorker?.controller;
    if (!sw) return ok(false);
    if (quitar) {
      sw.postMessage({ tipo: "quitar", url });
      return ok(true);
    }
    const alRecibir = (e: MessageEvent) => {
      if (e.data?.url !== url) return;
      navigator.serviceWorker.removeEventListener("message", alRecibir);
      ok(e.data.tipo === "guardada");
    };
    navigator.serviceWorker.addEventListener("message", alRecibir);
    sw.postMessage({ tipo: "guardar", url });
  });
}
