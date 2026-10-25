// Spots de observación de fauna (observatorios de OSM con especies y meses de GBIF). Servidor y navegador.

export interface Especie {
  nombre: string | null;
  cientifico: string | null;
  clase: "ave" | "mamifero";
  /** observaciones registradas a ~2 km (2016-2025) */
  n: number;
}

export interface LugarFauna {
  id: string;
  nombre: string;
  lat: number;
  lon: number;
  provincia: string;
  ccaa: string;
  osm: string;
  observatorios: number;
  accesible: boolean;
  observaciones: number;
  n_especies: number;
  especies: Especie[];
  /** observaciones por mes, de enero a diciembre */
  meses: number[];
}

export interface Fauna {
  fuentes: Record<string, string>;
  lugares: LugarFauna[];
}

export function nombreEspecie(e: Especie): string {
  return e.nombre ?? e.cientifico ?? "Especie sin nombre";
}

/** Meses (0-11) con al menos la mitad de las observaciones del mes con más. */
export function mesesBuenos(l: Pick<LugarFauna, "meses">): number[] {
  const max = Math.max(...l.meses);
  return max ? l.meses.map((v, i) => (v >= max / 2 ? i : -1)).filter((i) => i >= 0) : [];
}

/** Con pocas observaciones la lista de especies dice poco: se avisa. */
export const POCAS_OBSERVACIONES = 200;
