// Safaris en todo el mundo: parques curados a mano y enriquecidos con iNaturalist, Wikidata, ERA5 y OSM.
// Servidor y navegador.

export interface FotoSafari {
  url: string;
  autor: string | null;
  licencia: string | null;
  web?: string | null;
}

export interface TaxonSafari {
  taxon: number;
  cientifico: string;
  nombre: string | null;
  grupo: string | null;
  foto: FotoSafari | null;
  /** observaciones verificables en iNaturalist alrededor del parque */
  n?: number;
}

export interface Alojamiento {
  nombre: string;
  tipo: string;
  lat: number;
  lon: number;
  web: string | null;
  telefono: string | null;
  estrellas: string | null;
  osm: string;
}

export interface Parque {
  id: string;
  nombre: string;
  pais: string;
  continente: string;
  wikidata: string | null;
  lat: number;
  lon: number;
  radio_km: number;
  tipos: string[];
  /** meses recomendados (1-12), escritos a mano */
  meses: number[];
  /** taxones de iNaturalist de sus especies estrella */
  estrella: number[];
  tasa: string | null;
  consejo: string;
  web?: string;
  es?: string;
  foto?: FotoSafari | null;
  especies?: Record<string, TaxonSafari[]>;
  conteo_estrella?: Record<string, number>;
  /** observaciones de mamíferos por mes, 0-100 (null si hay muy pocas) */
  meses_mamiferos?: number[] | null;
  observaciones?: number;
  clima?: { lluvia_mm: number[]; tmax: (number | null)[] };
  alojamientos?: Alojamiento[];
}

export interface EspecieSafari extends TaxonSafari {
  parques: { id: string; n: number }[];
}

export interface Safaris {
  generado: string;
  fuentes: Record<string, string>;
  parques: Parque[];
  especies: EspecieSafari[];
}

export interface Recientes {
  fecha: string;
  desde: string;
  parques: Record<
    string,
    {
      estrella: Record<string, number>;
      mamiferos: { taxon: number; cientifico: string; nombre: string | null; n: number }[];
      observaciones: number;
    }
  >;
}

export const CONTINENTES = ["África", "Asia", "América", "Oceanía", "Europa"] as const;

export const TEXTO_TIPO: Record<string, string> = {
  "4x4": "En 4x4 con guía",
  "a pie": "A pie",
  "en coche propio": "En coche propio",
  globo: "En globo",
  barco: "En barco",
  canoa: "En canoa",
  primates: "Seguimiento de primates",
  nocturno: "Nocturno",
  buceo: "Buceo",
  autobús: "En autobús",
  avioneta: "En avioneta",
  "vehículo de tundra": "En vehículo de tundra",
};

export function nombreTaxon(t: Pick<TaxonSafari, "nombre" | "cientifico">): string {
  return t.nombre ?? t.cientifico;
}

/** Identificador legible para la URL de una especie: «panthera-leo». */
export function slugEspecie(t: Pick<TaxonSafari, "cientifico">): string {
  return t.cientifico.toLowerCase().replace(/[^a-z]+/g, "-");
}

export function enTemporada(p: Pick<Parque, "meses">, mes: number): boolean {
  return p.meses.includes(mes + 1);
}

/**
 * Orden de «mejor ahora»: primero los parques en temporada, luego los que más especies estrella han tenido
 * en los últimos 30 días (si hay datos recientes) o en total.
 */
export function puntuacionAhora(p: Parque, mes: number, recientes?: Recientes | null): number {
  const r = recientes?.parques[p.id];
  const vistas = r
    ? Object.values(r.estrella).reduce((a, b) => a + b, 0)
    : Object.values(p.conteo_estrella ?? {}).reduce((a, b) => a + b, 0) / 50;
  return (enTemporada(p, mes) ? 1000 : 0) + Math.min(999, vistas);
}

/** Enlace de Google Maps para leer reseñas de un alojamiento (no hay reseñas abiertas y gratuitas). */
export function enlaceResenas(a: Pick<Alojamiento, "nombre" | "lat" | "lon">): string {
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${a.nombre} ${a.lat},${a.lon}`)}`;
}
