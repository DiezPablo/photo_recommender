// El punto más alto de una ruta (normalmente el mirador o la cumbre de la foto) y cuánto se tarda en subir y
// en volver, con el método MIDE (el mismo que rasante.rutas.metricas). Puro: servidor y navegador.
import { distanciaKm } from "@/features/eventos/modelo";
import { type Ruta, trozos } from "@/features/rutas/modelo";

export interface Cima {
  lat: number;
  lon: number;
  alt: number;
  /** km desde la salida */
  km: number;
  horasSubida: number;
  /** de la cima al final de la ruta (circular) o de vuelta a la salida por el mismo camino (lineal) */
  horasBajada: number;
  vuelta: "sigue" | "misma";
}

/** Horas MIDE: 4 km/h en llano, 400 m/h subiendo, 600 m/h bajando; el mayor más la mitad del menor. */
export function horasMide(km: number, subida: number, bajada: number): number {
  const th = km / 4;
  const tv = subida / 400 + bajada / 600;
  return Math.max(th, tv) + Math.min(th, tv) / 2;
}

/** Subida y bajada acumuladas con histéresis de 3 m (como el pipeline) en un tramo del perfil. */
function desnivel(perfil: [number, number][]): { subida: number; bajada: number } {
  let subida = 0;
  let bajada = 0;
  let ref = perfil[0]?.[1] ?? 0;
  for (const [, alt] of perfil) {
    if (alt - ref >= 3) {
      subida += alt - ref;
      ref = alt;
    } else if (ref - alt >= 3) {
      bajada += ref - alt;
      ref = alt;
    }
  }
  return { subida, bajada };
}

/** Punto del trazado a `km` de la salida, recorriendo los trozos en orden. */
function puntoA(r: Ruta, km: number): [number, number] {
  let acumulado = 0;
  let ultimo: [number, number] = r.inicio;
  for (const trozo of trozos(r.linea)) {
    for (let i = 1; i < trozo.length; i++) {
      const [a, b] = [trozo[i - 1], trozo[i]];
      const d = distanciaKm({ lat: a[0], lon: a[1] }, { lat: b[0], lon: b[1] });
      if (acumulado + d >= km) {
        const f = d ? (km - acumulado) / d : 0;
        return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
      }
      acumulado += d;
      ultimo = b;
    }
  }
  return ultimo;
}

/** null si la ruta apenas sube (no hay «cima») o si llegar arriba lleva más de una jornada. */
export function cimaDe(r: Ruta): Cima | null {
  const perfil = r.perfil;
  if (perfil.length < 2 || (r.alt_max ?? 0) - (r.alt_min ?? 0) < 100) return null;
  let i = 0;
  for (let j = 1; j < perfil.length; j++) if (perfil[j][1] > perfil[i][1]) i = j;
  const [km, alt] = perfil[i];
  if (km < 0.3) return null; // el punto más alto es la salida: es una ruta de bajada
  const ida = desnivel(perfil.slice(0, i + 1));
  const horasSubida = horasMide(km, ida.subida, ida.bajada);
  if (horasSubida > 8) return null;
  let horasBajada: number;
  let vuelta: Cima["vuelta"];
  const kmTotal = perfil[perfil.length - 1][0];
  if (r.circular) {
    const resto = desnivel(perfil.slice(i));
    horasBajada = horasMide(kmTotal - km, resto.subida, resto.bajada);
    vuelta = "sigue";
  } else {
    // por el mismo camino: lo que se subió se baja
    horasBajada = horasMide(km, ida.bajada, ida.subida);
    vuelta = "misma";
  }
  const [lat, lon] = puntoA(r, km);
  return { lat, lon, alt, km, horasSubida, horasBajada, vuelta };
}

export interface Paso {
  /** km desde la salida hasta el punto del trazado más cercano */
  km: number;
  /** distancia (km) del lugar al trazado */
  distancia: number;
  lat: number;
  lon: number;
  horasIda: number;
  /** vuelta por el mismo camino */
  horasVuelta: number;
}

/** Si la ruta pasa a menos de `maxKm` del lugar: dónde, a cuántos km de la salida y cuánto se tarda. */
export function pasoPor(r: Ruta, lat: number, lon: number, maxKm = 0.3): Paso | null {
  const k = Math.cos((lat * Math.PI) / 180);
  let mejor: { d: number; km: number; p: [number, number] } | null = null;
  let acumulado = 0;
  for (const trozo of trozos(r.linea)) {
    for (let i = 1; i < trozo.length; i++) {
      const [a, b] = [trozo[i - 1], trozo[i]];
      // proyección sobre el segmento en un plano local (a estas distancias basta)
      const ax = (a[1] - lon) * k;
      const ay = a[0] - lat;
      const bx = (b[1] - lon) * k;
      const by = b[0] - lat;
      const dx = bx - ax;
      const dy = by - ay;
      const t = dx || dy ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / (dx * dx + dy * dy))) : 0;
      const d = Math.hypot(ax + t * dx, ay + t * dy) * 111.2;
      const largo = distanciaKm({ lat: a[0], lon: a[1] }, { lat: b[0], lon: b[1] });
      if (!mejor || d < mejor.d)
        mejor = { d, km: acumulado + t * largo, p: [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])] };
      acumulado += largo;
    }
  }
  if (!mejor || mejor.d > maxKm) return null;
  const tramo = r.perfil.filter(([x]) => x <= mejor.km);
  const ida = desnivel(tramo.length ? tramo : r.perfil.slice(0, 1));
  return {
    km: Math.round(mejor.km * 10) / 10,
    distancia: mejor.d,
    lat: mejor.p[0],
    lon: mejor.p[1],
    horasIda: horasMide(mejor.km, ida.subida, ida.bajada),
    horasVuelta: horasMide(mejor.km, ida.bajada, ida.subida),
  };
}
