// ¿Se puede volar un dron en cada spot? (public/datos/dron.json; solo servidor). Zonas UAS de ENAIRE y espacios
// protegidos de la Agencia Europea de Medio Ambiente, calculado una vez al mes.
import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

export type NivelDron = "no" | "permiso" | "condiciones" | "libre";

export interface ZonaDron {
  capa: "aero" | "infraestructura" | "protegido" | "natura";
  nivel: Exclude<NivelDron, "libre">;
  nombre?: string;
  texto: string;
  desde_m?: number;
  hasta_m?: number;
}

interface Dron {
  fecha: string;
  fuentes: Record<string, string>;
  zonas: Record<string, ZonaDron>;
  spots: Record<string, { estado: NivelDron; zonas?: string[] }>;
}

export const TEXTO_NIVEL: Record<NivelDron, string> = {
  no: "No, sin autorización expresa",
  permiso: "Con permiso",
  condiciones: "Con condiciones",
  libre: "Sin zonas restringidas",
};

export const CAPA: Record<ZonaDron["capa"], string> = {
  aero: "Espacio aéreo",
  infraestructura: "Infraestructura",
  protegido: "Espacio protegido",
  natura: "Red Natura 2000",
};

let cache: Dron | null | undefined;

export function cargarDron(): Dron | null {
  if (cache !== undefined) return cache;
  const f = path.join(process.cwd(), "public", "datos", "dron.json");
  cache = existsSync(f) ? (JSON.parse(readFileSync(f, "utf8")) as Dron) : null;
  return cache;
}

/** Estado del spot y sus zonas, de la más a la menos restrictiva; null si aún no hay datos o el spot es nuevo. */
export function dronDe(id: string): { estado: NivelDron; zonas: ZonaDron[]; fecha: string } | null {
  const d = cargarDron();
  const s = d?.spots[id];
  if (!d || !s) return null;
  return { estado: s.estado, zonas: (s.zonas ?? []).map((z) => d.zonas[z]).filter(Boolean), fecha: d.fecha };
}
