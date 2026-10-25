// Climatología por mes (ERA5 2021-2025): tipos y utilidades puras.

export type SerieClima = "atardecer" | "amanecer" | "noche" | "niebla";
export const SERIES: SerieClima[] = ["atardecer", "amanecer", "noche", "niebla"];

export const NOMBRE_SERIE: Record<SerieClima, string> = {
  atardecer: "Atardeceres buenos",
  amanecer: "Amaneceres buenos",
  noche: "Noches despejadas",
  niebla: "Madrugadas con niebla",
};

export const NOMBRE_CORTO_SERIE: Record<SerieClima, string> = {
  atardecer: "Atardecer",
  amanecer: "Amanecer",
  noche: "Noche",
  niebla: "Niebla",
};

export interface PuntoClima {
  lat: number;
  lon: number;
  /** % por mes, de enero a diciembre (null si no hay datos) */
  atardecer: (number | null)[];
  amanecer: (number | null)[];
  noche: (number | null)[];
  niebla: (number | null)[];
}

export interface Clima {
  generado: string;
  desde: string;
  hasta: string;
  paso: number;
  nota_buena: number;
  horas_noche: number;
  puntos: PuntoClima[];
}

/** El punto de la rejilla más cercano (si está a menos de un paso: fuera de España no hay datos). */
export function climaDe(c: Clima | null, lat: number, lon: number): PuntoClima | null {
  if (!c) return null;
  let mejor: PuntoClima | null = null;
  let dMin = Infinity;
  const k = Math.cos((lat * Math.PI) / 180);
  for (const p of c.puntos) {
    const d = (p.lat - lat) ** 2 + ((p.lon - lon) * k) ** 2;
    if (d < dMin) {
      dMin = d;
      mejor = p;
    }
  }
  return dMin <= c.paso ** 2 ? mejor : null;
}

/** El mes (0-11) con más frecuencia en una serie. */
export function mejorMes(p: PuntoClima, s: SerieClima): number | null {
  let mejor: number | null = null;
  p[s].forEach((v, i) => {
    if (v !== null && (mejor === null || v > (p[s][mejor] ?? -1))) mejor = i;
  });
  return mejor;
}

/** «1 de cada 3» para porcentajes: más fácil de leer que «33 %». */
export function deCada(pct: number): string {
  if (pct <= 0) return "casi nunca";
  if (pct >= 90) return "casi siempre";
  const n = Math.round(100 / pct);
  return n <= 1 ? "casi siempre" : `1 de cada ${n}`;
}
