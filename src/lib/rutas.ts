// Lectura de public/datos/rutas.json en el build (solo servidor).
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import type { Ruta } from "./modeloRutas";

export * from "./modeloRutas";

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
  return [...n].map(([ccaa, k]) => ({ ccaa, slug: slugCcaa(ccaa), n: k })).sort((a, b) => a.ccaa.localeCompare(b.ccaa));
}

function slugCcaa(c: string) {
  return c.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
