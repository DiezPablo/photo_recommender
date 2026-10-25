// Logística de OpenStreetMap cerca de spots y rutas (public/datos/logistica.json; solo servidor).
import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

export type TipoLogistica = "aparcamiento" | "fuente" | "refugio" | "autocaravanas" | "camping";

export interface PuntoLogistica {
  tipo: TipoLogistica;
  detalle?: string;
  nombre?: string;
  lat: number;
  lon: number;
  osm: string;
  km: number;
}

interface Logistica {
  radios: Record<TipoLogistica, number>;
  spots: Record<string, PuntoLogistica[]>;
  rutas: Record<string, PuntoLogistica[]>;
}

let cache: Logistica | null | undefined;

export function cargarLogistica(): Logistica | null {
  if (cache !== undefined) return cache;
  const f = path.join(process.cwd(), "public", "datos", "logistica.json");
  cache = existsSync(f) ? (JSON.parse(readFileSync(f, "utf8")) as Logistica) : null;
  return cache;
}
