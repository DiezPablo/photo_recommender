// Filas del ranking de un día y tipo de salida (solo servidor: lee los datos con datos.ts).
import type { FilaRanking } from "@/components/tipos";
import { calificacion, cargar, type Filtro, horaDe, miniatura, motivos, notaDe } from "./datos";

/** Cuántos spots se envían en el HTML (sin JavaScript se ve este top). El resto, en JSON aparte. */
export const TOP_HTML = 60;

export function filasRanking(d: number, filtro: Filtro): FilaRanking[] {
  return cargar()
    .spots.map((s) => {
      const dia = s.dias[d];
      const n = notaDe(dia, filtro);
      if (!dia || !n) return null;
      return {
        bruta: n.nota.desglose.reduce((a, f) => a + f.puntos, 0),
        calidad: s.descubierto?.puntuacion ?? 0,
        id: s.id, nombre: s.nombre, lat: s.lat, lon: s.lon, tipo: s.tipo,
        nota: n.nota.nota, clase: calificacion(n.nota.nota).clase, momento: n.momento,
        hora: horaDe(dia, n.momento),
        motivos: motivos(n.nota).map((m) => m.texto),
        autores: s.descubierto?.fotografos ?? 0,
        dudosa: n.nota.confianza === "baja",
        provincia: s.provincia ?? s.descubierto?.provincia ?? null,
        ccaa: s.ccaa ?? s.descubierto?.ccaa ?? null,
        foto: miniatura(s.descubierto?.galeria?.[0]?.url, 120),
      };
    })
    .filter((f) => f !== null)
    // A escala nacional muchos spots llegan al 10: desempata la nota sin recortar y después la calidad del
    // spot (popularidad en Commons y cielo oscuro, de descubrir_espana.py)
    .sort((a, b) => b.nota - a.nota || b.bruta - a.bruta || b.calidad - a.calidad || a.nombre.localeCompare(b.nombre))
    .map(({ bruta: _b, calidad: _c, ...f }) => f as FilaRanking);
}

export function urlRanking(d: number, filtro: Filtro): string {
  return `/datos-ranking/${d}/${filtro}`;
}
