// Lectura de los datos que publica el pipeline (solo servidor). En Vercel están comprimidos en datos/*.gz, fuera
// de public/: así no se publican como estáticos (el navegador solo pide fauna.json y safaris_indice.json) y las
// funciones ISR llevan ~10 veces menos peso. En local, si no hay .gz, se usa public/datos (salida del pipeline).
import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { gunzipSync } from "node:zlib";

const COMPRIMIDOS = path.join(process.cwd(), "datos");
const LOCALES = path.join(process.cwd(), "public", "datos");

export function leerDatos<T>(nombre: string): T | null {
  const gz = path.join(COMPRIMIDOS, `${nombre}.gz`);
  if (existsSync(gz)) return JSON.parse(gunzipSync(readFileSync(gz)).toString("utf8")) as T;
  const local = path.join(LOCALES, nombre);
  return existsSync(local) ? (JSON.parse(readFileSync(local, "utf8")) as T) : null;
}
