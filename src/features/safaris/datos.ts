// Lectura de public/datos/safaris.json y safaris_recientes.json (solo servidor).
import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import type { EspecieSafari, Parque, Recientes, Safaris } from "@/features/safaris/modelo";
import { slugEspecie } from "@/features/safaris/modelo";

export * from "@/features/safaris/modelo";

function leer<T>(nombre: string): T | null {
  const f = path.join(process.cwd(), "public", "datos", nombre);
  return existsSync(f) ? (JSON.parse(readFileSync(f, "utf8")) as T) : null;
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
