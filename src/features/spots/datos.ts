// Lectura de los JSON que publica el pipeline (public/datos) en tiempo de build.
// Vercel reconstruye la web con cada commit de datos, así que las páginas son estáticas.
// Solo para el servidor: los componentes de cliente importan de "./modelo".
import "server-only";
import { leerDatos } from "@/lib/datos";
import type { Informe, Spot, SpotDescubierto } from "@/features/spots/modelo";

export * from "@/features/spots/modelo";

function leer<T>(fichero: string): T | null {
  return leerDatos<T>(fichero);
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
