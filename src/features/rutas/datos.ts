// Lectura de public/datos/rutas.json en el build (solo servidor).
import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { type Cima, cimaDe } from "@/features/rutas/cima";
import { distanciaKm } from "@/features/eventos/modelo";
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

/** Rutas cuyo punto más alto queda a menos de `radioKm` del punto: las que suben a un spot. */
export function rutasQueSuben(lat: number, lon: number, radioKm = 1): { ruta: Ruta; cima: Cima; km: number }[] {
  const cerca = [];
  for (const r of cargarRutas().rutas) {
    // descarte rápido por la caja de la ruta antes de calcular la cima
    const [oeste, sur, este, norte] = r.bbox;
    const margen = radioKm / 100;
    if (lat < sur - margen || lat > norte + margen || lon < oeste - margen || lon > este + margen) continue;
    const cima = cimaDeRuta(r);
    if (!cima) continue;
    const km = distanciaKm(cima, { lat, lon });
    if (km <= radioKm) cerca.push({ ruta: r, cima, km });
  }
  return cerca.sort((a, b) => a.cima.horasSubida - b.cima.horasSubida);
}
