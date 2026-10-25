// Tipos y utilidades del calendario de eventos (servidor y navegador).

export type Categoria = "flora" | "otono" | "fauna" | "paisaje" | "agua" | "nieve";

export interface EventoNaturaleza {
  id: string;
  nombre: string;
  categoria: Categoria;
  /** fechas habituales MM-DD: se repiten cada año (si desde > hasta, cruza el año) */
  desde: string;
  hasta: string;
  pico: string;
  lugar: string;
  provincia: string | null;
  ccaa: string | null;
  lat: number;
  lon: number;
  radio_km: number;
  descripcion: string;
  consejo: string;
}

export interface FaseLuna {
  fecha: string;
  hora: string;
  fase: "nueva" | "llena";
}

export interface LluviaMeteoros {
  id: string;
  nombre: string;
  fecha: string;
  /** la noche (fecha de la tarde) en la que se observa el máximo */
  noche: string;
  thz: number;
  luna: { iluminacion: number; arriba: boolean };
  calidad: "buena" | "regular" | "mala";
  descripcion: string;
}

export interface Eclipse {
  id: string;
  nombre: string;
  fecha: string;
  descripcion: string;
  consejo: string;
  fuente: string;
}

export interface VentanaViaLactea {
  desde: string;
  hasta: string;
  luna_nueva: string;
  horas_max: number;
}

export interface Eventos {
  generado: string;
  desde: string;
  hasta: string;
  luna: FaseLuna[];
  meteoros: LluviaMeteoros[];
  eclipses: Eclipse[];
  via_lactea: { horas_por_mes: number[]; ventanas: VentanaViaLactea[] };
  naturaleza: EventoNaturaleza[];
  categorias: Record<Categoria, string>;
}

export const MESES = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
];
const MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
export const INICIALES = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];

/** Día del año (1-365, año no bisiesto) de una fecha MM-DD. */
function diaDelAno(md: string): number {
  const [m, d] = md.split("-").map(Number);
  return Math.round((Date.UTC(2027, m - 1, d) - Date.UTC(2027, 0, 1)) / 864e5) + 1;
}

/** Tramos [ini, fin] en días del año que ocupa el evento (dos si cruza el año). */
function tramos(e: Pick<EventoNaturaleza, "desde" | "hasta">): [number, number][] {
  const a = diaDelAno(e.desde);
  const b = diaDelAno(e.hasta);
  return a <= b
    ? [[a, b]]
    : [
        [a, 365],
        [1, b],
      ];
}

/** ¿Está el evento en marcha algún día del mes (0-11)? */
export function activoEnMes(e: Pick<EventoNaturaleza, "desde" | "hasta">, mes: number): boolean {
  const ini = diaDelAno(`${String(mes + 1).padStart(2, "0")}-01`);
  const fin = mes === 11 ? 365 : diaDelAno(`${String(mes + 2).padStart(2, "0")}-01`) - 1;
  return tramos(e).some(([a, b]) => a <= fin && b >= ini);
}

/** ¿Está en marcha en esta fecha (YYYY-MM-DD)? */
export function activoEn(e: Pick<EventoNaturaleza, "desde" | "hasta">, fecha: string): boolean {
  const d = diaDelAno(fecha.slice(5));
  return tramos(e).some(([a, b]) => a <= d && d <= b);
}

export function mesDe(md: string): number {
  return Number(md.slice(0, 2)) - 1;
}

/** "03-15" → "15 mar"; "2027-03-15" → "15 mar". */
export function fechaCorta(f: string): string {
  const md = f.length > 5 ? f.slice(5) : f;
  const [m, d] = md.split("-").map(Number);
  return `${d} ${MESES_CORTOS[m - 1]}`;
}

/** "2027-08-02" → "lunes 2 de agosto de 2027". */
export function fechaLarga(f: string, conAno = true): string {
  const d = new Date(`${f}T12:00:00Z`);
  return d.toLocaleDateString("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: conAno ? "numeric" : undefined,
    timeZone: "UTC",
  });
}

/** Próxima temporada del evento a partir de hoy: fechas completas con año. */
export function proximaTemporada(e: EventoNaturaleza, hoy: string): { desde: string; hasta: string; ahora: boolean } {
  const ano = Number(hoy.slice(0, 4));
  const cruza = diaDelAno(e.desde) > diaDelAno(e.hasta);
  for (const a of [ano - 1, ano, ano + 1]) {
    const desde = `${a}-${e.desde}`;
    const hasta = `${cruza ? a + 1 : a}-${e.hasta}`;
    if (hasta >= hoy) return { desde, hasta, ahora: desde <= hoy };
  }
  return { desde: `${ano + 1}-${e.desde}`, hasta: `${cruza ? ano + 2 : ano + 1}-${e.hasta}`, ahora: false };
}

/** Año en el que cae el mes (0-11) dentro del calendario publicado (los próximos 12 meses). */
export function anoDelMes(eventos: Pick<Eventos, "desde">, mes: number): number {
  const ano = Number(eventos.desde.slice(0, 4));
  return mes >= Number(eventos.desde.slice(5, 7)) - 1 ? ano : ano + 1;
}

export function distanciaKm(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const r = Math.PI / 180;
  const h =
    Math.sin(((b.lat - a.lat) * r) / 2) ** 2 +
    Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(((b.lon - a.lon) * r) / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}

export const TEXTO_CALIDAD: Record<LluviaMeteoros["calidad"], string> = {
  buena: "Sin luna que moleste",
  regular: "Luna grande, pero bajo el horizonte en el máximo",
  mala: "La luna estorba",
};
