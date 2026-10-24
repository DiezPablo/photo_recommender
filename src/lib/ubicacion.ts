// Ubicación del usuario compartida entre el ranking y el mapa (solo en el navegador).
export interface Ubicacion {
  lat: number;
  lon: number;
}

export function leerUbicacion(): Ubicacion | null {
  try {
    const u = JSON.parse(localStorage.getItem("ubicacion") ?? "null");
    return u && typeof u.lat === "number" && typeof u.lon === "number" ? u : null;
  } catch {
    return null;
  }
}

export function guardarUbicacion(u: Ubicacion | null) {
  try {
    if (u) localStorage.setItem("ubicacion", JSON.stringify(u));
    else localStorage.removeItem("ubicacion");
  } catch {}
  window.dispatchEvent(new CustomEvent("ubicacion", { detail: u }));
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
          error: "Has bloqueado la ubicación para esta web. Actívala en los ajustes del navegador (en iPhone: Ajustes › Privacidad › Localización › Safari) y vuelve a pulsar.",
        });
      if (reintento)
        return navigator.geolocation.getCurrentPosition(exito, (e2) => fallo(e2, false), { enableHighAccuracy: false, maximumAge: 3600000, timeout: 20000 });
      resolver({ ok: false, error: "No llega la señal de ubicación. Comprueba que la localización del móvil está activada e inténtalo de nuevo." });
    };
    navigator.geolocation.getCurrentPosition(exito, (e) => fallo(e, true), { enableHighAccuracy: false, maximumAge: 600000, timeout: 12000 });
  });
}
