// Tipos del informe y utilidades puras: se pueden usar tanto en el servidor como en el navegador.

export type Momento = "amanecer" | "atardecer" | "astro" | "niebla" | "luna";
export const MOMENTOS: Momento[] = ["amanecer", "atardecer", "astro", "niebla", "luna"];
export type Filtro = Momento | "todos";
export const FILTROS: Filtro[] = ["todos", ...MOMENTOS];

export const NOMBRE_MOMENTO: Record<Filtro, string> = {
  todos: "Todo",
  amanecer: "Amanecer",
  atardecer: "Atardecer",
  astro: "Noche y Vía Láctea",
  niebla: "Niebla y mar de nubes",
  luna: "Salida o puesta de luna",
};
export const NOMBRE_CORTO: Record<Filtro, string> = {
  todos: "Todo",
  amanecer: "Amanecer",
  atardecer: "Atardecer",
  astro: "Noche",
  niebla: "Niebla",
  luna: "Luna",
};

export interface Factor {
  texto: string;
  puntos: number;
}
export interface NotaMomento {
  nota: number;
  desglose: Factor[];
  avisos: string[];
  /** acuerdo entre dos modelos meteorológicos (ECMWF y el de alta resolución) */
  confianza?: "alta" | "media" | "baja" | null;
  modelo?: Record<string, unknown>;
}

export const TEXTO_CONFIANZA: Record<string, string> = {
  alta: "Los modelos coinciden",
  media: "Los modelos difieren algo",
  baja: "Previsión dudosa: los modelos no coinciden",
};
export type Tramo = [string | null, string | null];

export interface MeteoMomento {
  nubes_bajas: number;
  nubes_medias: number;
  nubes_altas: number;
  nubes_horizonte: number;
  visibilidad_km: number;
  lluvia: number;
  viento: number;
  temperatura: number;
  humedad: number;
}
export interface MeteoNoche {
  nubes: number;
  humedad: number;
  viento: number;
  rachas: number | null;
  temp_min: number | null;
  punto_rocio: number | null;
  margen_rocio: number | null;
  vapor_mm?: number | null;
  aod?: number | null;
  cupula?: { zona: string; km: number; hacia?: string } | null;
}

export interface Dia {
  fecha: string;
  fiabilidad: "alta" | "media" | "baja";
  sol: {
    amanecer: string | null;
    atardecer: string | null;
    az_amanecer: number | null;
    az_atardecer: number | null;
    dorada_manana: Tramo | null;
    dorada_tarde: Tramo | null;
    azul_manana: Tramo | null;
    azul_tarde: Tramo | null;
    /** hora a la que el sol asoma / se esconde tras el relieve y ángulo del relieve en esa dirección */
    amanecer_relieve?: string | null;
    atardecer_relieve?: string | null;
    relieve_amanecer?: number | null;
    relieve_atardecer?: number | null;
  };
  noche: {
    ini: string | null;
    fin: string | null;
    horas: number | null;
    luna: {
      fase: string;
      iluminacion: number;
      edad: number;
      salida: string | null;
      puesta: string | null;
      sin_luna: Tramo[];
      horas_sin_luna: number | null;
      evento?: EventoLuna | null;
    };
    via_lactea: {
      tramos: Tramo[];
      horas: number | null;
      horas_sin_luna: number | null;
      altura_max: number | null;
      azimut_max: number | null;
      hora_max: string | null;
      azimut_ini: number | null;
      azimut_fin: number | null;
    };
  };
  meteo: { amanecer?: MeteoMomento; atardecer?: MeteoMomento; noche?: MeteoNoche };
  notas: Partial<Record<Momento, NotaMomento>>;
  avisos: string[];
}

export interface EventoLuna {
  tipo: "salida" | "puesta";
  hora: string;
  azimut: number;
  horizonte: number;
  iluminacion: number;
  altura_sol: number;
}

export interface Contaminacion {
  zona: string;
  sqm: number;
  bortle: number;
  descripcion: string;
}

export interface SpotInforme {
  id: string;
  nombre: string;
  lat: number;
  lon: number;
  tipo: string | null;
  origen: string;
  elevacion: number | null;
  contaminacion: Contaminacion | null;
  horizonte: { amanecer?: [number, number]; atardecer?: [number, number] };
  provincia?: string | null;
  ccaa?: string | null;
  /** zona de sus horas (Canarias: Atlantic/Canary); los informes antiguos no la traen */
  zona_horaria?: string;
  dias: Dia[];
}

export interface Informe {
  generado: string;
  zona_horaria: string;
  fechas: string[];
  fuentes: Record<string, string>;
  spots: SpotInforme[];
}

export interface Foto {
  url: string;
  enlace: string;
  autor: string;
  licencia: string;
  titulo: string;
  fecha: string | null;
}

export interface SpotDescubierto {
  id: string;
  nombre: string;
  origen: string;
  fotos: number;
  fotografos: number;
  fotos_calidad: number;
  puntuacion: number;
  mejor_momento: string;
  pct_amanecer: number;
  pct_atardecer: number;
  pct_noche: number;
  meses: number[];
  meses_top: number[];
  galeria: Foto[];
  tipo_osm: string | null;
  direccion_vista: string | null;
  provincia?: string | null;
  ccaa?: string | null;
  wikidata?: string | null;
  /** horizonte del terreno: ángulos (décimas de grado) cada 360/n grados desde el norte */
  horizonte?: { elevacion: number; angulos: number[] } | null;
}

/** Spot del informe + lo que se sabe de él por Commons/OSM (si lo hay). */
export interface Spot extends SpotInforme {
  descubierto: SpotDescubierto | null;
}

/** Nota del spot para un día y filtro; con "todos", el mejor momento del día. */
export function notaDe(dia: Dia | undefined, filtro: Filtro): { momento: Momento; nota: NotaMomento } | null {
  if (!dia) return null;
  if (filtro !== "todos") {
    const n = dia.notas[filtro];
    return n ? { momento: filtro, nota: n } : null;
  }
  let mejor: { momento: Momento; nota: NotaMomento } | null = null;
  for (const m of MOMENTOS) {
    const n = dia.notas[m];
    if (n && (!mejor || n.nota > mejor.nota.nota)) mejor = { momento: m, nota: n };
  }
  return mejor;
}

/** Hora clave del momento para mostrarla en el ranking. */
export function horaDe(dia: Dia, momento: Momento): string {
  switch (momento) {
    case "amanecer":
      return dia.sol.amanecer_relieve ?? dia.sol.amanecer ?? "—";
    case "atardecer":
      return dia.sol.atardecer_relieve ?? dia.sol.atardecer ?? "—";
    case "niebla":
      return dia.sol.amanecer ? `madrugada · ${dia.sol.amanecer}` : "madrugada";
    case "luna": {
      const e = dia.noche.luna.evento;
      return e ? `${e.tipo === "salida" ? "sale" : "se pone"} ${e.hora}` : "—";
    }
    case "astro": {
      const sl = dia.noche.luna.sin_luna;
      if (dia.noche.luna.horas_sin_luna && sl.length && dia.noche.luna.horas_sin_luna < (dia.noche.horas ?? 0) - 0.2)
        return `sin luna ${sl[0][0]}–${sl[sl.length - 1][1]}`;
      return dia.noche.ini ? `${dia.noche.ini}–${dia.noche.fin}` : "—";
    }
  }
}

/** Los factores que más pesan (en valor absoluto), sin la base. */
export function motivos(n: NotaMomento, cuantos = 2): Factor[] {
  return [...n.desglose.slice(1)].sort((a, b) => Math.abs(b.puntos) - Math.abs(a.puntos)).slice(0, cuantos);
}

export function calificacion(nota: number): { texto: string; clase: string } {
  if (nota >= 8) return { texto: "Excelente", clase: "n-top" };
  if (nota >= 6.5) return { texto: "Buena", clase: "n-buena" };
  if (nota >= 4.5) return { texto: "Regular", clase: "n-regular" };
  return { texto: "Floja", clase: "n-floja" };
}

const DIAS_SEMANA = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
export const MESES_LARGOS = [
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

export function etiquetaDia(fecha: string, indice: number): { corto: string; largo: string } {
  const d = new Date(`${fecha}T12:00:00Z`);
  const semana = DIAS_SEMANA[d.getUTCDay()];
  const fechaCorta = `${d.getUTCDate()} ${MESES[d.getUTCMonth()]}`;
  const corto = indice === 0 ? "Hoy" : indice === 1 ? "Mañana" : semana.slice(0, 3);
  return { corto, largo: `${semana} ${fechaCorta}` };
}

export function rumbo(az: number | null | undefined): string {
  if (az === null || az === undefined) return "—";
  const nombres = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"];
  return `${nombres[Math.round(az / 22.5) % 16]} ${Math.round(az)}°`;
}

export function tramoTexto(t: Tramo | null | undefined): string {
  if (!t || !t[0]) return "—";
  return `${t[0]}–${t[1]}`;
}

export const TEXTO_AVISO: Record<string, string> = {
  reflejos: "Reflejos: viento casi nulo sobre el agua",
  rocio: "Riesgo de rocío en la lente: lleva calentador o capucha",
  mar_de_nubes: "Posible mar de nubes",
  techo_nubes_cerca: "El techo de las nubes bajas está a la altura del spot: puede quedar dentro o justo encima",
};

/** Miniatura de Commons de otro ancho (Commons solo sirve anchos estándar: 120, 250, 330, 500, 960…). */
export function miniatura(url: string | null | undefined, ancho: 120 | 250 | 330 | 500 | 960): string | null {
  if (!url) return null;
  return /\/\d+px-/.test(url) ? url.replace(/\/\d+px-/, `/${ancho}px-`) : url;
}
