// Filas del ranking de un día y tipo de salida (solo servidor: lee los datos con datos.ts).
import "server-only";
import type { FilaRanking } from "@/features/spots/tipos";
import { calificacion, cargar, type Filtro, horaDe, miniatura, motivos, notaDe } from "@/features/spots/datos";

/** Cuántos spots se envían en el HTML (sin JavaScript se ve este top). El resto, en JSON aparte. */
export const TOP_HTML = 60;

export function filasRanking(d: number, filtro: Filtro): FilaRanking[] {
  const candidatas: { fila: FilaRanking; bruta: number; calidad: number }[] = [];
  for (const s of cargar().spots) {
    const dia = s.dias[d];
    const n = notaDe(dia, filtro);
    if (!dia || !n) continue;
    candidatas.push({
      // para desempatar: la nota antes de recortarla a 10 y la calidad del spot
      bruta: n.nota.desglose.reduce((a, f) => a + f.puntos, 0),
      calidad: s.descubierto?.puntuacion ?? 0,
      fila: {
        id: s.id,
        nombre: s.nombre,
        lat: s.lat,
        lon: s.lon,
        tipo: s.tipo,
        nota: n.nota.nota,
        clase: calificacion(n.nota.nota).clase,
        momento: n.momento,
        hora: horaDe(dia, n.momento),
        motivos: motivos(n.nota).map((m) => m.texto),
        autores: s.descubierto?.fotografos ?? 0,
        dudosa: n.nota.confianza === "baja",
        provincia: s.provincia ?? s.descubierto?.provincia ?? null,
        ccaa: s.ccaa ?? s.descubierto?.ccaa ?? null,
        foto: miniatura(s.descubierto?.galeria?.[0]?.url, 120),
      },
    });
  }
  // A escala nacional muchos spots llegan al 10: desempata la nota sin recortar y después la calidad del
  // spot (popularidad en Commons y cielo oscuro, calculada en `python -m rasante spots`)
  return candidatas
    .sort(
      (a, b) =>
        b.fila.nota - a.fila.nota ||
        b.bruta - a.bruta ||
        b.calidad - a.calidad ||
        a.fila.nombre.localeCompare(b.fila.nombre),
    )
    .map((c) => c.fila);
}

export function urlRanking(d: number, filtro: Filtro): string {
  return `/datos-ranking/${d}/${filtro}`;
}
