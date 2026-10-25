// Lectura de public/datos/fauna.json (solo servidor) y cruces con spots y eventos.
import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { distanciaKm } from "@/features/eventos/modelo";
import type { Fauna, LugarFauna } from "@/features/fauna/modelo";

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
