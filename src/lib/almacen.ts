"use client";
// Estado que vive fuera de React (localStorage, la URL) leído con useSyncExternalStore: sin desajustes de
// hidratación (en el servidor se usa el valor por defecto) y sin efectos que copien ese estado a React.
import { useCallback, useMemo, useSyncExternalStore } from "react";

const nada = () => () => {};

/** true en el navegador una vez hidratada la página (false en el HTML del servidor). */
export function useHidratado(): boolean {
  return useSyncExternalStore(
    nada,
    () => true,
    () => false,
  );
}

// ------------------------------------------------------------ localStorage ----
const EVENTO_ALMACEN = "almacen";

function suscribirAlmacen(aviso: () => void) {
  window.addEventListener(EVENTO_ALMACEN, aviso);
  window.addEventListener("storage", aviso); // cambios desde otra pestaña
  return () => {
    window.removeEventListener(EVENTO_ALMACEN, aviso);
    window.removeEventListener("storage", aviso);
  };
}

export function leerAlmacen(clave: string): string | null {
  try {
    return localStorage.getItem(clave);
  } catch {
    return null; // modo privado o almacenamiento bloqueado
  }
}

export function escribirAlmacen(clave: string, valor: string | null): void {
  try {
    if (valor === null) localStorage.removeItem(clave);
    else localStorage.setItem(clave, valor);
  } catch {}
  window.dispatchEvent(new Event(EVENTO_ALMACEN));
}

/** Texto guardado en localStorage (null si no hay). */
export function useAlmacen(clave: string): string | null {
  return useSyncExternalStore(
    suscribirAlmacen,
    () => leerAlmacen(clave),
    () => null,
  );
}

/** Número guardado como preferencia (p. ej. el radio de búsqueda), con su valor por defecto. */
export function usePreferenciaNumero(clave: string, defecto: number): [number, (v: number) => void] {
  const bruto = useAlmacen(clave);
  const valor = bruto !== null && Number.isFinite(Number(bruto)) ? Number(bruto) : defecto;
  const cambiar = useCallback((v: number) => escribirAlmacen(clave, String(v)), [clave]);
  return [valor, cambiar];
}

/** Texto guardado como preferencia (p. ej. la comunidad elegida), con su valor por defecto. */
export function usePreferenciaTexto(clave: string, defecto: string): [string, (v: string) => void] {
  const valor = useAlmacen(clave) ?? defecto;
  const cambiar = useCallback((v: string) => escribirAlmacen(clave, v), [clave]);
  return [valor, cambiar];
}

// --------------------------------------------------------------------- URL ----
const EVENTO_URL = "parametros-url";

function suscribirUrl(aviso: () => void) {
  window.addEventListener(EVENTO_URL, aviso);
  window.addEventListener("popstate", aviso);
  return () => {
    window.removeEventListener(EVENTO_URL, aviso);
    window.removeEventListener("popstate", aviso);
  };
}

/** Parámetros de la URL como estado (se escriben con replaceState: no recargan ni llenan el historial). */
export function useParametrosUrl(): [URLSearchParams, (cambios: Record<string, string | null>) => void] {
  const busqueda = useSyncExternalStore(
    suscribirUrl,
    () => window.location.search,
    () => "",
  );
  const parametros = useMemo(() => new URLSearchParams(busqueda), [busqueda]);
  const actualizar = useCallback((cambios: Record<string, string | null>) => {
    const p = new URLSearchParams(window.location.search);
    for (const [k, v] of Object.entries(cambios)) {
      if (v === null || v === "") p.delete(k);
      else p.set(k, v);
    }
    const q = p.toString();
    window.history.replaceState(window.history.state, "", q ? `?${q}` : window.location.pathname);
    window.dispatchEvent(new Event(EVENTO_URL));
  }, []);
  return [parametros, actualizar];
}
