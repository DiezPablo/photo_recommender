// Lectura de public/datos/fauna.json (solo servidor) y cruces con spots y eventos.
import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { distanciaKm } from "@/features/eventos/modelo";
import type { Especies, FichaEspecie } from "@/features/fauna/especies";
import type { Fauna, LugarFauna } from "@/features/fauna/modelo";

export * from "@/features/fauna/especies";
export * from "@/features/fauna/modelo";

let cache: Fauna | null | undefined;

export function cargarFauna(): Fauna | null {
  if (cache !== undefined) return cache;
  const f = path.join(process.cwd(), "public", "datos", "fauna.json");
  cache = existsSync(f) ? (JSON.parse(readFileSync(f, "utf8")) as Fauna) : null;
  return cache;
}

export function getLugar(id: string): LugarFauna | undefined {
  return cargarFauna()?.lugares.find((l) => l.id === id);
}

/** Lugares de fauna a menos de `km` de un punto, del más cercano al más lejano. */
export function faunaCerca(lat: number, lon: number, km = 10): (LugarFauna & { km: number })[] {
  return (cargarFauna()?.lugares ?? [])
    .map((l) => ({ ...l, km: distanciaKm(l, { lat, lon }) }))
    .filter((l) => l.km <= km)
    .sort((a, b) => a.km - b.km);
}

let cacheEspecies: Especies | null | undefined;

export function cargarEspecies(): Especies | null {
  if (cacheEspecies !== undefined) return cacheEspecies;
  const f = path.join(process.cwd(), "public", "datos", "especies.json");
  cacheEspecies = existsSync(f) ? (JSON.parse(readFileSync(f, "utf8")) as Especies) : null;
  return cacheEspecies;
}

export function getEspecie(id: string): FichaEspecie | undefined {
  return cargarEspecies()?.especies.find((e) => e.id === id);
}

/** Ficha de una especie emblemática por su nombre científico (para enlazarla desde los observatorios). */
export function especiePorCientifico(cientifico: string | null): FichaEspecie | undefined {
  return cientifico ? cargarEspecies()?.especies.find((e) => e.cientifico === cientifico) : undefined;
}

/** Observatorios donde la especie está entre las más vistas, de más a menos observaciones. */
export function lugaresConEspecie(cientifico: string, max = 8): (LugarFauna & { nEspecie: number })[] {
  return (cargarFauna()?.lugares ?? [])
    .flatMap((l) => {
      const e = l.especies.find((x) => x.cientifico === cientifico);
      return e ? [{ ...l, nEspecie: e.n }] : [];
    })
    .sort((a, b) => b.nEspecie - a.nEspecie)
    .slice(0, max);
}

/** Especies emblemáticas que se buscan en un evento del calendario (berrea → ciervo). */
export function especiesDeEvento(id: string): FichaEspecie[] {
  return (cargarEspecies()?.especies ?? []).filter((e) => e.eventos.includes(id));
}
