// Lectura de public/datos/clima.json en el build (solo servidor). Mientras la rejilla no esté completa no
// existe y las secciones de climatología no se muestran.
import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import type { Clima } from "@/features/clima/modelo";

export * from "@/features/clima/modelo";

let cache: Clima | null | undefined;

export function cargarClima(): Clima | null {
  if (cache !== undefined) return cache;
  const f = path.join(process.cwd(), "public", "datos", "clima.json");
  cache = existsSync(f) ? (JSON.parse(readFileSync(f, "utf8")) as Clima) : null;
  return cache;
}
