// Lectura de los JSON que publica el pipeline (public/datos) en tiempo de build.
// Vercel reconstruye la web con cada commit de datos, así que las páginas son estáticas.
// Solo para el servidor: los componentes de cliente importan de "./modelo".
import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import type { Informe, Spot, SpotDescubierto } from "@/features/spots/modelo";

export * from "@/features/spots/modelo";

const DIR = path.join(process.cwd(), "public", "datos");

function leer<T>(fichero: string): T | null {
  const ruta = path.join(DIR, fichero);
  if (!existsSync(ruta)) return null;
  return JSON.parse(readFileSync(ruta, "utf8")) as T;
}

let cache: { informe: Informe | null; spots: Spot[] } | null = null;

export function cargar(): { informe: Informe | null; spots: Spot[] } {
  if (cache) return cache;
  const informe = leer<Informe>("informe.json");
  const geo = leer<{ features: { properties: SpotDescubierto }[] }>("spots.geojson");
  const porId = new Map<string, SpotDescubierto>();
  for (const f of geo?.features ?? []) porId.set(f.properties.id, f.properties);
  const spots: Spot[] = (informe?.spots ?? []).map((s) => ({ ...s, descubierto: porId.get(s.id) ?? null }));
  cache = { informe, spots };
  return cache;
}

export function getSpot(id: string): Spot | undefined {
  return cargar().spots.find((s) => s.id === id);
}
