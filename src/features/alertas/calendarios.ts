// Calendarios suscribibles por zona: los mejores momentos previstos (nota ≥ 8) y el calendario del cielo y de
// la naturaleza. Solo servidor: lee el informe y los eventos del build, que se rehace dos veces al día.
import "server-only";
import { calendario, type EventoIcs, utcDesdeLocal } from "@/lib/ics";
import { anoDelMes, cargarEventos, fechaCorta } from "@/features/eventos/datos";
import { cargar } from "@/features/spots/datos";
import { type Dia, type Momento, MOMENTOS, motivos, NOMBRE_MOMENTO, type Spot } from "@/features/spots/modelo";
import { slug } from "@/features/rutas/modelo";

export const SITIO = process.env.NEXT_PUBLIC_SITIO ?? "https://photo-recommender.vercel.app";
export const NOTA_ALERTA = 8;
const MIN = 60000;

export interface Zona {
  slug: string;
  nombre: string;
  /** null = toda España */
  ccaa: string | null;
  /** momentos por día como máximo */
  porDia: number;
}

export function zonas(): Zona[] {
  const ccaa = [
    ...new Set(
      cargar()
        .spots.map((s) => s.ccaa)
        .filter((c): c is string => !!c),
    ),
  ].sort((a, b) => a.localeCompare(b, "es"));
  return [
    { slug: "espana", nombre: "Toda España", ccaa: null, porDia: 5 },
    ...ccaa.map((c) => ({ slug: slug(c), nombre: c, ccaa: c, porDia: 3 })),
  ];
}

/** Franja horaria del momento: de la hora azul al final de la dorada, la noche sin luna, la madrugada… */
function franja(dia: Dia, m: Momento, zona: string): [Date, Date] | null {
  const a = (h: string | null | undefined, extraDia = 0) =>
    h ? utcDesdeLocal(extraDia ? siguiente(dia.fecha) : dia.fecha, h, zona) : null;
  const s = dia.sol;
  switch (m) {
    case "amanecer": {
      const ini = a(s.azul_manana?.[0] ?? s.amanecer);
      const fin = a(s.dorada_manana?.[1] ?? s.amanecer);
      return ini && fin ? [ini, fin] : null;
    }
    case "atardecer": {
      const ini = a(s.dorada_tarde?.[0] ?? s.atardecer);
      const fin = a(s.azul_tarde?.[1] ?? s.atardecer);
      return ini && fin ? [ini, fin] : null;
    }
    case "niebla": {
      const sale = a(s.amanecer);
      return sale ? [new Date(sale.getTime() - 90 * MIN), new Date(sale.getTime() + 30 * MIN)] : null;
    }
    case "luna": {
      const e = dia.noche.luna.evento;
      const t = e ? a(e.hora) : null;
      return t ? [new Date(t.getTime() - 30 * MIN), new Date(t.getTime() + 30 * MIN)] : null;
    }
    case "astro": {
      const sl = dia.noche.luna.sin_luna;
      const [hi, hf] = sl.length ? [sl[0][0], sl[sl.length - 1][1]] : [dia.noche.ini, dia.noche.fin];
      if (!hi || !hf) return null;
      // la noche empieza la tarde de `fecha`: lo que va de madrugada es del día siguiente
      const ini = a(hi, hi < "12:00" ? 1 : 0);
      const fin = a(hf, hf < "12:00" ? 1 : 0);
      return ini && fin ? [ini, fin] : null;
    }
  }
}

function siguiente(f: string): string {
  return new Date(Date.parse(`${f}T00:00:00Z`) + 864e5).toISOString().slice(0, 10);
}

function momentosBuenos(spots: Spot[], zona: Zona, tz: string): EventoIcs[] {
  const eventos: EventoIcs[] = [];
  const fechas = [...new Set(spots.flatMap((s) => s.dias.map((d) => d.fecha)))].sort();
  for (const fecha of fechas) {
    const candidatos: { s: Spot; d: Dia; m: Momento; nota: number }[] = [];
    for (const s of spots) {
      if (zona.ccaa && s.ccaa !== zona.ccaa) continue;
      const d = s.dias.find((x) => x.fecha === fecha);
      if (!d) continue;
      for (const m of MOMENTOS) {
        const n = d.notas[m];
        if (n && n.nota >= NOTA_ALERTA) candidatos.push({ s, d, m, nota: n.nota });
      }
    }
    candidatos.sort((a, b) => b.nota - a.nota);
    const vistos = new Set<string>();
    for (const c of candidatos) {
      if (vistos.has(c.s.id) || vistos.size >= zona.porDia) continue;
      const f = franja(c.d, c.m, c.s.zona_horaria ?? tz);
      if (!f) continue;
      vistos.add(c.s.id);
      const n = c.d.notas[c.m]!;
      const nota = c.nota.toLocaleString("es-ES", { maximumFractionDigits: 1, minimumFractionDigits: 1 });
      const porque = motivos(n)
        .map((x) => `${x.texto} (${x.puntos > 0 ? "+" : ""}${x.puntos.toLocaleString("es-ES")})`)
        .join("; ");
      eventos.push({
        uid: `${c.s.id}-${fecha}-${c.m}@rasante`,
        titulo: `${NOMBRE_MOMENTO[c.m]} ${nota} · ${c.s.nombre}`,
        descripcion:
          `${porque}.` +
          (c.d.fiabilidad === "baja" ? " Previsión a varios días: puede cambiar." : "") +
          ` Se actualiza dos veces al día. ${SITIO}/spot/${c.s.id}`,
        lugar: [c.s.nombre, c.s.provincia].filter(Boolean).join(", "),
        geo: { lat: c.s.lat, lon: c.s.lon },
        url: `${SITIO}/spot/${c.s.id}`,
        inicio: f[0],
        fin: f[1],
      });
    }
  }
  return eventos;
}

function eventosDelCielo(zona: Zona): EventoIcs[] {
  const ev = cargarEventos();
  if (!ev) return [];
  const lista: EventoIcs[] = [];
  for (const l of ev.luna) {
    lista.push({
      uid: `luna-${l.fecha}@rasante`,
      titulo: l.fase === "nueva" ? "Luna nueva: noches oscuras" : "Luna llena",
      dia: l.fecha,
      url: `${SITIO}/calendario`,
    });
  }
  for (const m of ev.meteoros) {
    lista.push({
      uid: `${m.id}@rasante`,
      titulo: `${m.nombre} (máximo) · luna al ${m.luna.iluminacion} %`,
      descripcion: `Hasta ${m.thz} meteoros por hora en condiciones ideales. ${m.descripcion}`,
      dia: m.noche,
      url: `${SITIO}/calendario`,
    });
  }
  for (const v of ev.via_lactea.ventanas) {
    lista.push({
      uid: `vl-${v.luna_nueva}@rasante`,
      titulo: "Vía Láctea sin luna",
      descripcion: `Noches con el núcleo alto y sin luna: hasta ${v.horas_max} h por noche.`,
      dia: v.desde,
      diaFin: v.hasta,
      url: `${SITIO}/calendario`,
    });
  }
  const a = ev.aurora;
  if (a?.noche && a.nivel !== "ninguno") {
    lista.push({
      uid: `aurora-${a.noche}@rasante`,
      titulo: `Posible aurora${a.nivel === "norte" ? " en el norte" : ""} · Kp ${a.kp_max.toLocaleString("es-ES")}`,
      descripcion:
        "Tormenta geomagnética fuerte prevista por NOAA. Busca un sitio oscuro con el horizonte norte despejado; " +
        "la cámara la capta antes que el ojo.",
      dia: a.noche,
      url: a.fuente,
    });
  }
  for (const e of ev.eclipses) {
    lista.push({
      uid: `${e.id}@rasante`,
      titulo: e.nombre,
      descripcion: `${e.descripcion} ${e.consejo}`,
      dia: e.fecha,
      url: e.fuente,
    });
  }
  for (const n of ev.naturaleza) {
    if (zona.ccaa && n.ccaa !== zona.ccaa) continue;
    const mes = Number(n.pico.slice(0, 2)) - 1;
    const pico = `${anoDelMes(ev, mes)}-${n.pico}`;
    if (pico < ev.desde) continue;
    lista.push({
      uid: `${n.id}-${pico.slice(0, 4)}@rasante`,
      titulo: `${n.nombre}: en su mejor momento`,
      descripcion: `${n.descripcion} Habitualmente del ${fechaCorta(n.desde)} al ${fechaCorta(n.hasta)}. ${n.consejo}`,
      lugar: [n.lugar, n.provincia].filter(Boolean).join(", "),
      geo: { lat: n.lat, lon: n.lon },
      dia: pico,
      url: `${SITIO}/evento/${n.id}`,
    });
  }
  return lista;
}

export function calendarioDeZona(z: Zona): string {
  const { informe, spots } = cargar();
  const tz = informe?.zona_horaria ?? "Europe/Madrid";
  return calendario(
    `Rasante · ${z.nombre}`,
    `Mejores momentos para fotografiar (nota ≥ ${NOTA_ALERTA}) y calendario del cielo y la naturaleza. ${SITIO}`,
    [...momentosBuenos(spots, z, tz), ...eventosDelCielo(z)],
  );
}
