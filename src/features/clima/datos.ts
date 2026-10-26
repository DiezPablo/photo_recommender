// Lectura de public/datos/clima.json en el build (solo servidor). Mientras la rejilla no esté completa no
// existe y las secciones de climatología no se muestran.
import "server-only";
import { leerDatos } from "@/lib/datos";
import type { Clima } from "@/features/clima/modelo";

export * from "@/features/clima/modelo";

let cache: Clima | null | undefined;

export function cargarClima(): Clima | null {
  if (cache !== undefined) return cache;
  cache = leerDatos<Clima>("clima.json");
  return cache;
}
