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
