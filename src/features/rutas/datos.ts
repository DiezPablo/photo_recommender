// Lectura de public/datos/rutas.json en el build (solo servidor).
import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { type Cima, cimaDe, type Paso, pasoPor } from "@/features/rutas/cima";
import { type Ruta, slug } from "@/features/rutas/modelo";

export * from "@/features/rutas/modelo";

let cache: { generado: string | null; rutas: Ruta[]; porId: Map<string, Ruta> } | null = null;

export function cargarRutas() {
  if (cache) return cache;
  const f = path.join(process.cwd(), "public", "datos", "rutas.json");
  const datos = existsSync(f) ? (JSON.parse(readFileSync(f, "utf8")) as { generado: string; rutas: Ruta[] }) : null;
  const rutas = datos?.rutas ?? [];
  cache = { generado: datos?.generado ?? null, rutas, porId: new Map(rutas.map((r) => [r.id, r])) };
  return cache;
}

export function getRuta(id: string): Ruta | undefined {
  return cargarRutas().porId.get(id);
}

export function comunidadesRutas(): { ccaa: string; slug: string; n: number }[] {
  const n = new Map<string, number>();
  for (const r of cargarRutas().rutas) n.set(r.ccaa, (n.get(r.ccaa) ?? 0) + 1);
  return [...n].map(([ccaa, k]) => ({ ccaa, slug: slug(ccaa), n: k })).sort((a, b) => a.ccaa.localeCompare(b.ccaa));
}

let cimas: Map<string, Cima | null> | null = null;

/** La cima de cada ruta, calculada una vez por proceso. */
export function cimaDeRuta(r: Ruta): Cima | null {
  cimas ??= new Map();
  if (!cimas.has(r.id)) cimas.set(r.id, cimaDe(r));
  return cimas.get(r.id) ?? null;
}

/** Rutas que pasan a menos de `maxKm` de un lugar (un spot): por dónde, a cuántos km de la salida y en
 * cuánto tiempo; primero las que llegan antes. Se descartan las que tardan más de una jornada en llegar. */
export function rutasQuePasan(lat: number, lon: number, maxKm = 0.3): { ruta: Ruta; paso: Paso }[] {
  const margen = maxKm / 100;
  const lista = [];
  for (const r of cargarRutas().rutas) {
    const [oeste, sur, este, norte] = r.bbox;
    if (lat < sur - margen || lat > norte + margen || lon < oeste - margen || lon > este + margen) continue;
    const paso = pasoPor(r, lat, lon, maxKm);
    if (paso && paso.horasIda <= 8) lista.push({ ruta: r, paso });
  }
  return lista.sort((a, b) => a.paso.horasIda - b.paso.horasIda);
}
