// Ubicación del usuario compartida entre el ranking, el buscador de rutas y los mapas (solo en el navegador).
import { useMemo } from "react";
import { escribirAlmacen, leerAlmacen, useAlmacen } from "@/lib/almacen";

const CLAVE = "ubicacion";

export interface Ubicacion {
  lat: number;
  lon: number;
}

function interpretar(texto: string | null): Ubicacion | null {
  try {
    const u = JSON.parse(texto ?? "null");
    return u && typeof u.lat === "number" && typeof u.lon === "number" ? u : null;
  } catch {
    return null;
  }
}

export function leerUbicacion(): Ubicacion | null {
  return interpretar(leerAlmacen(CLAVE));
}

export function guardarUbicacion(u: Ubicacion | null) {
  escribirAlmacen(CLAVE, u ? JSON.stringify(u) : null);
}

/** La ubicación guardada, que se actualiza en todos los componentes al pedirla u olvidarla. */
export function useUbicacion(): Ubicacion | null {
  const texto = useAlmacen(CLAVE);
  return useMemo(() => interpretar(texto), [texto]);
}

export function distanciaKm(a: Ubicacion, b: Ubicacion): number {
  const r = Math.PI / 180;
  const h =
    Math.sin(((b.lat - a.lat) * r) / 2) ** 2 +
    Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(((b.lon - a.lon) * r) / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}

/** Pide la ubicación al navegador. Si tarda o falla la precisa, reintenta con la aproximada (antena/wifi).
 * Devuelve la ubicación o un texto que explica qué pasa y cómo arreglarlo. */
export function pedirUbicacion(): Promise<{ ok: true; ubic: Ubicacion } | { ok: false; error: string }> {
  return new Promise((resolver) => {
    if (!window.isSecureContext || !navigator.geolocation)
      return resolver({ ok: false, error: "Este navegador no permite pedir la ubicación en esta página." });
    const exito = (p: GeolocationPosition) => {
      const u = { lat: +p.coords.latitude.toFixed(3), lon: +p.coords.longitude.toFixed(3) };
      guardarUbicacion(u);
      resolver({ ok: true, ubic: u });
    };
    const fallo = (e: GeolocationPositionError, reintento: boolean) => {
      if (e.code === e.PERMISSION_DENIED)
        return resolver({
          ok: false,
          error:
            "Has bloqueado la ubicación para esta web. Actívala en los ajustes del navegador (en iPhone: Ajustes › Privacidad › Localización › Safari) y vuelve a pulsar.",
        });
      if (reintento)
        return navigator.geolocation.getCurrentPosition(exito, (e2) => fallo(e2, false), {
          enableHighAccuracy: false,
          maximumAge: 3600000,
          timeout: 20000,
        });
      resolver({
        ok: false,
        error:
          "No llega la señal de ubicación. Comprueba que la localización del móvil está activada e inténtalo de nuevo.",
      });
    };
    navigator.geolocation.getCurrentPosition(exito, (e) => fallo(e, true), {
      enableHighAccuracy: false,
      maximumAge: 600000,
      timeout: 12000,
    });
  });
}
