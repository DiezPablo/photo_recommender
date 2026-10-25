// Especies emblemáticas (lince, oso, grulla…): dónde y cuándo se ven en España según GBIF. Servidor y navegador.

export type Grupo = "mamifero" | "ave" | "marino";

export const GRUPOS: Record<Grupo, string> = { mamifero: "Mamíferos", ave: "Aves", marino: "Cetáceos" };

export interface ZonaEspecie {
  lat: number;
  lon: number;
  provincia: string;
  ccaa: string;
  /** observaciones estimadas en la celda de ~25 km, relativas a la zona con más (100) */
  peso: number;
}

export interface FotoEspecie {
  url: string;
  web: string | null;
  autor: string | null;
  licencia: string | null;
}

export interface FichaEspecie {
  id: string;
  nombre: string;
  cientifico: string;
  grupo: Grupo;
  gbif: number;
  observaciones: number;
  /** de 0 a 100: observaciones del mes frente al esfuerzo de observación de ese mes */
  meses: number[];
  zonas: ZonaEspecie[];
  eventos: string[];
  consejo: string;
  foto: FotoEspecie | null;
}

export interface Especies {
  fuentes: Record<string, string>;
  especies: FichaEspecie[];
}

/** Lo justo para buscar una especie desde el navegador. */
export type EspecieBreve = Pick<FichaEspecie, "id" | "nombre" | "cientifico">;

/** Provincias de las zonas, en orden de importancia y sin repetir. */
export function provinciasDe(e: Pick<FichaEspecie, "zonas">, max = 4): string[] {
  return [...new Set(e.zonas.map((z) => z.provincia))].slice(0, max);
}

/** Meses en que es más fácil verla (índice ≥ 70); vacío si da igual el mes (más de seis). */
export function mesesFaciles(e: Pick<FichaEspecie, "meses">): number[] {
  const m = e.meses.map((v, i) => (v >= 70 ? i : -1)).filter((i) => i >= 0);
  return m.length > 6 ? [] : m;
}

/** «noviembre a enero» si los meses van seguidos (también pasando por enero); si no, la lista. */
export function resumirMeses(meses: number[], nombres: readonly string[]): string {
  const dentro = new Set(meses);
  const inicio = meses.find((m) => !dentro.has((m + 11) % 12));
  if (inicio !== undefined) {
    let fin = inicio;
    while (dentro.has((fin + 1) % 12) && (fin + 1) % 12 !== inicio) fin = (fin + 1) % 12;
    const largo = ((fin - inicio + 12) % 12) + 1;
    if (largo === meses.length) return largo === 1 ? nombres[inicio] : `${nombres[inicio]} a ${nombres[fin]}`;
  }
  return meses.map((m) => nombres[m]).join(", ");
}

/** Radio del círculo de una zona en el mapa: más grande cuantas más observaciones. */
export function radioZona(z: ZonaEspecie): number {
  return 6 + (8 * z.peso) / 100;
}
