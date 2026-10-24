// Tipos y utilidades de las rutas de senderismo (servidor y navegador).

export type TipoRuta = "GR" | "PR" | "SL" | "Europeo" | "Camino de Santiago" | "Camino Natural" | "Vía Verde" | "Sendero";
export const TIPOS_RUTA: TipoRuta[] = ["GR", "PR", "SL", "Camino Natural", "Camino de Santiago", "Vía Verde", "Europeo", "Sendero"];
export type Dificultad = "fácil" | "moderada" | "difícil" | "muy difícil";
export const DIFICULTADES: Dificultad[] = ["fácil", "moderada", "difícil", "muy difícil"];

export interface Ruta {
  id: string;
  nombre: string;
  ref: string | null;
  tipo: TipoRuta;
  fuente: string;
  osm: number | null;
  oficial: string | null;
  web: string | null;
  operador: string | null;
  desde: string | null;
  hasta: string | null;
  descripcion: string | null;
  wikidata: string | null;
  km: number;
  subida: number;
  bajada: number;
  alt_max: number | null;
  alt_min: number | null;
  horas: number;
  dificultad: Dificultad;
  circular: boolean;
  provincia: string;
  ccaa: string;
  inicio: [number, number];
  fin: [number, number];
  bbox: [number, number, number, number];
  perfil: [number, number][];
  linea: string;
  linea_mapa: string;
}

/** Lo que viaja al navegador para listar y filtrar todas las rutas. */
export interface FilaRuta {
  id: string;
  nombre: string;
  ref: string | null;
  tipo: TipoRuta;
  km: number;
  subida: number;
  horas: number;
  dificultad: Dificultad;
  circular: boolean;
  provincia: string;
  ccaa: string;
  lat: number;
  lon: number;
}

export function filaRuta(r: Ruta): FilaRuta {
  return {
    id: r.id, nombre: r.nombre, ref: r.ref, tipo: r.tipo, km: r.km, subida: r.subida, horas: r.horas,
    dificultad: r.dificultad, circular: r.circular, provincia: r.provincia, ccaa: r.ccaa,
    lat: r.inicio[0], lon: r.inicio[1],
  };
}

/** Celdas de 1° para servir los trazados del mapa general por zonas. */
export function celda(lat: number, lon: number): string {
  return `${Math.floor(lat)}_${Math.floor(lon)}`;
}

/** Decodifica una «encoded polyline» → [[lat, lon], …]. */
export function decodificar(s: string, precision = 5): [number, number][] {
  const factor = 10 ** precision;
  const puntos: [number, number][] = [];
  let i = 0, lat = 0, lon = 0;
  while (i < s.length) {
    for (const eje of [0, 1]) {
      let res = 0, sh = 0, b;
      do {
        b = s.charCodeAt(i++) - 63;
        res |= (b & 0x1f) << sh;
        sh += 5;
      } while (b >= 0x20);
      const d = res & 1 ? ~(res >> 1) : res >> 1;
      if (eje === 0) lat += d;
      else lon += d;
    }
    puntos.push([lat / factor, lon / factor]);
  }
  return puntos;
}

export function duracion(h: number): string {
  const total = Math.round(h * 4) * 15; // a cuartos de hora: es una estimación
  const hh = Math.floor(total / 60), mm = total % 60;
  return hh ? (mm ? `${hh} h ${mm} min` : `${hh} h`) : `${mm} min`;
}

export function slug(t: string): string {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

export const RANGOS_KM: { id: string; texto: string; min: number; max: number }[] = [
  { id: "corta", texto: "Hasta 8 km", min: 0, max: 8 },
  { id: "media", texto: "8-15 km", min: 8, max: 15 },
  { id: "larga", texto: "15-25 km", min: 15, max: 25 },
  { id: "muy-larga", texto: "25-50 km", min: 25, max: 50 },
  { id: "etapas", texto: "Más de 50 km", min: 50, max: Infinity },
];
