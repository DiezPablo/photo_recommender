// Logística de OpenStreetMap cerca de spots y rutas (public/datos/logistica.json; solo servidor).
import "server-only";
import { leerDatos } from "@/lib/datos";

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
  cache = leerDatos<Logistica>("logistica.json");
  return cache;
}
