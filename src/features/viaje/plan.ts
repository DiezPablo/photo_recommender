// Plan de viaje: para una zona y unas fechas, qué hacer cada día (amanecer, ruta, atardecer y noche).
// Dentro de la previsión (5 días) manda la nota prevista; más allá, la climatología (lo habitual ese mes),
// el calendario (naturaleza, meteoros, eclipses), las alineaciones y la luna. Solo servidor.
import "server-only";
import { cargarClima, climaDe, type PuntoClima } from "@/features/clima/datos";
import {
  activoEn,
  type Alineacion,
  cargarAlineaciones,
  cargarEventos,
  distanciaKm,
  type EventoNaturaleza,
} from "@/features/eventos/datos";
import { cargarRutas, filaRuta, rutasQueSuben, slug } from "@/features/rutas/datos";
import { planDia } from "@/features/rutas/planLuz";
import { cargar, type Momento, type Spot } from "@/features/spots/datos";
import { lunaDeLaNoche } from "@/lib/luna";
import { horaLocal, horaSol } from "@/lib/sol";

export const MAX_DIAS = 7;
/** la ruta del día tiene que caber entre el amanecer y el atardecer, con tiempo para las fotos */
const HORAS_RUTA_DIA = 6;
const CERCA_KM_DEFECTO = 60;

export interface Zona {
  /** slug de la comunidad o "espana" */
  zona: string;
  cerca?: { lat: number; lon: number; km: number };
}

export interface SpotPlan {
  id: string;
  nombre: string;
  provincia: string | null;
  lat: number;
  lon: number;
}

export interface Propuesta {
  momento: "amanecer" | "atardecer" | "noche" | "luna";
  spot: SpotPlan;
  /** nota prevista (si el día está en la previsión) */
  nota?: number;
  /** % de días buenos ese mes según la climatología (si no hay previsión) */
  pct?: number;
  hora?: string;
  /** cómo subir andando para tenerlo arriba */
  ruta?: { id: string; nombre: string; salida: string; horas: number };
}

export interface DiaPlan {
  fecha: string;
  previsto: boolean;
  luna: number;
  amanecer?: Propuesta;
  atardecer?: Propuesta;
  noche?: Propuesta;
  ruta?: { id: string; nombre: string; km: number; subida: number; horas: number; dificultad: string; cerca: string };
  naturaleza: EventoNaturaleza[];
  alineaciones: { spot: SpotPlan; a: Alineacion }[];
  cielo: string[];
}

export function comunidades(): { slug: string; nombre: string }[] {
  const n = [
    ...new Set(
      cargar()
        .spots.map((s) => s.ccaa)
        .filter((c): c is string => !!c),
    ),
  ];
  return n.sort((a, b) => a.localeCompare(b, "es")).map((c) => ({ slug: slug(c), nombre: c }));
}

function enZona(z: Zona, p: { lat: number; lon: number; ccaa?: string | null }): boolean {
  if (z.cerca) return distanciaKm(z.cerca, p) <= z.cerca.km;
  return z.zona === "espana" || (!!p.ccaa && slug(p.ccaa) === z.zona);
}

const plano = (s: Spot): SpotPlan => ({
  id: s.id,
  nombre: s.nombre,
  provincia: s.provincia ?? null,
  lat: s.lat,
  lon: s.lon,
});

function siguiente(f: string, n = 1): string {
  return new Date(Date.parse(`${f}T12:00:00Z`) + n * 864e5).toISOString().slice(0, 10);
}

/** El mejor spot para un momento: por nota prevista o, sin previsión, por climatología. Se evita repetir. */
function elegir(
  spots: Spot[],
  fecha: string,
  momento: Momento,
  usados: Set<string>,
  clima: (s: Spot) => PuntoClima | null,
): { s: Spot; nota?: number; pct?: number } | null {
  const mes = Number(fecha.slice(5, 7)) - 1;
  const serie = momento === "astro" ? "noche" : momento === "amanecer" ? "amanecer" : "atardecer";
  const candidatos = spots
    .map((s) => {
      const d = s.dias.find((x) => x.fecha === fecha);
      const n = d?.notas[momento]?.nota;
      if (n !== undefined) return { s, valor: n, nota: n };
      const c = clima(s)?.[serie][mes];
      if (c == null) return null;
      // de noche pesa también lo oscuro del cielo (SQM 22 = cielo prístino)
      const oscuridad = momento === "astro" ? Math.max(0, Math.min(1, ((s.contaminacion?.sqm ?? 19) - 19) / 3)) : 1;
      return { s, valor: (c / 10) * (0.4 + 0.6 * oscuridad) + (s.descubierto?.fotos ?? 0) / 1e4, pct: c };
    })
    .filter((x): x is NonNullable<typeof x> => x !== null)
    .sort((a, b) => b.valor - a.valor);
  // variedad: el mejor que no se haya usado, salvo que el repetido sea claramente mejor (≥ 1 punto)
  const nuevo = candidatos.find((c) => !usados.has(c.s.id));
  const mejor = candidatos[0];
  const c = nuevo && mejor && mejor.valor - nuevo.valor < 1 ? nuevo : mejor;
  return c ? { s: c.s, nota: "nota" in c ? c.nota : undefined, pct: "pct" in c ? c.pct : undefined } : null;
}

function propuesta(
  momento: Propuesta["momento"],
  fecha: string,
  e: { s: Spot; nota?: number; pct?: number },
): Propuesta {
  const { s } = e;
  // horas con el cálculo propio (hora local también en Canarias; el informe va en hora peninsular)
  const evLuna = momento === "luna" ? s.dias.find((x) => x.fecha === fecha)?.noche.luna.evento : null;
  const hora = evLuna
    ? evLuna.hora
    : momento === "noche" || momento === "luna"
      ? fmt(horaSol(fecha, s.lat, s.lon, -18, false), s.lon)
      : fmt(horaSol(fecha, s.lat, s.lon, -0.833, momento === "amanecer"), s.lon);
  const p: Propuesta = { momento, spot: plano(s), nota: e.nota, pct: e.pct, hora };
  if (momento === "amanecer" || momento === "atardecer") {
    const r = rutasQueSuben(s.lat, s.lon)[0];
    if (r) {
      const pl = planDia(fecha, r.cima.lat, r.cima.lon, r.cima.horasSubida, r.cima.horasBajada);
      const m = momento === "amanecer" ? pl.amanecer : pl.atardecer;
      if (m)
        p.ruta = {
          id: r.ruta.id,
          nombre: r.ruta.nombre,
          salida: horaLocal(m.salida, s.lon),
          horas: r.cima.horasSubida,
        };
    }
  }
  return p;
}

function fmt(d: Date | null, lon: number): string | undefined {
  return d ? horaLocal(d, lon) : undefined;
}

export function planificar(z: Zona, desde: string, dias: number): { dias: DiaPlan[]; spots: number } {
  const { spots: todos } = cargar();
  const spots = todos.filter((s) => enZona(z, s));
  const clima = cargarClima();
  const cacheClima = new Map<string, PuntoClima | null>();
  const climaSpot = (s: Spot) => {
    if (!cacheClima.has(s.id)) cacheClima.set(s.id, climaDe(clima, s.lat, s.lon));
    return cacheClima.get(s.id) ?? null;
  };
  const eventos = cargarEventos();
  const alineaciones = cargarAlineaciones();
  const porId = new Map(spots.map((s) => [s.id, s]));
  const rutas = cargarRutas().rutas.filter((r) => enZona(z, { lat: r.inicio[0], lon: r.inicio[1], ccaa: r.ccaa }));
  const usados = new Set<string>();
  const rutasUsadas = new Set<string>();
  const resultado: DiaPlan[] = [];

  for (let i = 0; i < Math.min(dias, MAX_DIAS); i++) {
    const fecha = siguiente(desde, i);
    const previsto = spots.some((s) => s.dias.some((d) => d.fecha === fecha));
    const dia: DiaPlan = { fecha, previsto, luna: lunaDeLaNoche(fecha), naturaleza: [], alineaciones: [], cielo: [] };
    for (const [momento, clave] of [
      ["amanecer", "amanecer"],
      ["atardecer", "atardecer"],
    ] as const) {
      const e = elegir(spots, fecha, clave, usados, climaSpot);
      if (!e) continue;
      usados.add(e.s.id);
      dia[momento] = propuesta(momento, fecha, e);
    }
    // de noche: con luna grande la Vía Láctea no sale; si la luna saliendo o poniéndose tiene mejor nota, manda
    const astro = elegir(spots, fecha, "astro", usados, climaSpot);
    const luna = previsto ? elegir(spots, fecha, "luna", usados, climaSpot) : null;
    const noche =
      luna?.nota !== undefined && (astro?.nota ?? 0) < luna.nota
        ? { e: luna, m: "luna" as const }
        : astro && { e: astro, m: "noche" as const };
    if (noche) {
      usados.add(noche.e.s.id);
      // sin previsión y con la luna por encima del 60 %, la Vía Láctea no se verá: noche de paisaje con luna
      const m = !previsto && dia.luna > 0.6 ? "luna" : noche.m;
      dia.noche = propuesta(m, fecha, noche.e);
    }
    // ruta del día: la que sube al spot del atardecer o del amanecer; si no, la mejor señalizada cerca de ellos
    const centro = dia.atardecer?.spot ?? dia.amanecer?.spot;
    if (centro) {
      const r = rutas
        .filter((x) => !rutasUsadas.has(x.id))
        .map((x) => ({ x, km: distanciaKm(centro, { lat: x.inicio[0], lon: x.inicio[1] }) }))
        .filter(({ x, km }) => km <= 25 && x.horas <= HORAS_RUTA_DIA)
        .sort((a, b) => filaRuta(b.x).rel - filaRuta(a.x).rel || a.km - b.km)[0];
      const sube = dia.atardecer?.ruta ?? dia.amanecer?.ruta;
      const subida = sube ? rutas.find((x) => x.id === sube.id) : undefined;
      const elegida = subida && subida.horas <= HORAS_RUTA_DIA ? subida : r?.x;
      if (elegida) {
        rutasUsadas.add(elegida.id);
        dia.ruta = {
          id: elegida.id,
          nombre: elegida.nombre,
          km: elegida.km,
          subida: elegida.subida,
          horas: elegida.horas,
          dificultad: elegida.dificultad,
          cerca: centro.nombre,
        };
      }
    }
    // naturaleza en marcha en la zona
    dia.naturaleza = (eventos?.naturaleza ?? []).filter(
      (e) => activoEn(e, fecha) && (z.cerca ? distanciaKm(z.cerca, e) <= z.cerca.km + e.radio_km : enZona(z, e)),
    );
    // alineaciones de ese día en spots de la zona
    for (const [id, lista] of Object.entries(alineaciones?.spots ?? {})) {
      const s = porId.get(id);
      if (!s) continue;
      for (const a of lista) if (a.fecha === fecha) dia.alineaciones.push({ spot: plano(s), a });
    }
    dia.alineaciones.sort(
      (a, b) => Number(b.a.cuerpo === "luna") - Number(a.a.cuerpo === "luna") || a.a.altura - b.a.altura,
    );
    dia.alineaciones = dia.alineaciones.slice(0, 3);
    // el cielo
    for (const l of eventos?.luna ?? []) if (l.fecha === fecha) dia.cielo.push(`Luna ${l.fase} a las ${l.hora}`);
    for (const m of eventos?.meteoros ?? [])
      if (m.noche === fecha) dia.cielo.push(`Máximo de las ${m.nombre} esta noche (luna al ${m.luna.iluminacion} %)`);
    for (const e of eventos?.eclipses ?? []) if (e.fecha === fecha) dia.cielo.push(`${e.nombre}: ${e.descripcion}`);
    const vl = eventos?.via_lactea.ventanas.find((v) => v.desde <= fecha && fecha <= v.hasta);
    if (vl) dia.cielo.push(`Vía Láctea sin luna: hasta ${vl.horas_max.toLocaleString("es-ES")} h de núcleo alto`);
    const au = eventos?.aurora;
    if (au?.noche === fecha && au.nivel !== "ninguno")
      dia.cielo.push(`Posible aurora (Kp ${au.kp_max.toLocaleString("es-ES")})`);
    resultado.push(dia);
  }
  return { dias: resultado, spots: spots.length };
}

export function zonaDesdeParametros(p: Record<string, string | string[] | undefined>): Zona {
  const v = (k: string) => (Array.isArray(p[k]) ? p[k][0] : p[k]);
  const lat = Number(v("lat"));
  const lon = Number(v("lon"));
  if (Number.isFinite(lat) && Number.isFinite(lon) && v("lat") && v("lon")) {
    const km = Math.min(300, Math.max(10, Number(v("km")) || CERCA_KM_DEFECTO));
    return { zona: "cerca", cerca: { lat, lon, km } };
  }
  return { zona: v("zona") || "espana" };
}
