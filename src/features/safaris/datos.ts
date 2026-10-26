// Lectura de public/datos/safaris.json y safaris_recientes.json (solo servidor).
import "server-only";
import { leerDatos } from "@/lib/datos";
import type { EspecieSafari, Mundo, Parque, ParqueMundo, Recientes, Safaris } from "@/features/safaris/modelo";
import { slugEspecie } from "@/features/safaris/modelo";

export * from "@/features/safaris/modelo";

function leer<T>(nombre: string): T | null {
  return leerDatos<T>(nombre);
}

let cache: Safaris | null | undefined;
let cacheRecientes: Recientes | null | undefined;

export function cargarSafaris(): Safaris | null {
  if (cache === undefined) cache = leer<Safaris>("safaris.json");
  return cache;
}

export function cargarRecientes(): Recientes | null {
  if (cacheRecientes === undefined) cacheRecientes = leer<Recientes>("safaris_recientes.json");
  return cacheRecientes;
}

export function getParque(id: string): Parque | undefined {
  return cargarSafaris()?.parques.find((p) => p.id === id);
}

export function getEspecieSafari(slug: string): EspecieSafari | undefined {
  return cargarSafaris()?.especies.find((e) => slugEspecie(e) === slug);
}

export function especiePorTaxon(taxon: number): EspecieSafari | undefined {
  return cargarSafaris()?.especies.find((e) => e.taxon === taxon);
}

let cacheMundo: Mundo | null | undefined;

export function cargarMundo(): Mundo | null {
  if (cacheMundo === undefined) cacheMundo = leer<Mundo>("safaris_mundo.json");
  return cacheMundo;
}

export function getParqueMundo(id: string): ParqueMundo | undefined {
  return cargarMundo()?.parques.find((p) => p.id === id);
}

/** Los mejores parques del mundo para una especie del catálogo (por su nombre científico). */
export function parquesMundoDe(cientifico: string, max = 25): { p: ParqueMundo; n: number }[] {
  const m = cargarMundo();
  if (!m) return [];
  const clave = Object.entries(m.estrella).find(([, c]) => c === cientifico)?.[0];
  if (!clave) return [];
  return m.parques
    .map((p) => ({ p, n: p.estrella[clave] ?? 0 }))
    .filter((x) => x.n >= 3)
    .sort((a, b) => b.n - a.n)
    .slice(0, max);
}
