// El plan de viaje como calendario .ics: cada amanecer, atardecer y noche propuestos con su spot.
import { SITIO } from "@/features/alertas/calendarios";
import { MAX_DIAS, planificar, type Propuesta, zonaDesdeParametros } from "@/features/viaje/plan";
import { calendario, type EventoIcs, utcDesdeLocal } from "@/lib/ics";
import { fechaLocal, zonaHoraria } from "@/lib/sol";

export const dynamic = "force-dynamic";

const TITULO: Record<Propuesta["momento"], string> = {
  amanecer: "Amanecer",
  atardecer: "Atardecer",
  noche: "Noche y Vía Láctea",
  luna: "Luna sobre el paisaje",
};

export function GET(req: Request) {
  const p = Object.fromEntries(new URL(req.url).searchParams);
  const hoy = fechaLocal(new Date());
  const desde = /^\d{4}-\d{2}-\d{2}$/.test(p.desde ?? "") && p.desde >= hoy ? p.desde : hoy;
  const dias = Math.min(MAX_DIAS, Math.max(1, Number(p.dias) || 3));
  const plan = planificar(zonaDesdeParametros(p), desde, dias);
  const eventos: EventoIcs[] = [];
  for (const d of plan.dias) {
    for (const pr of [d.amanecer, d.atardecer, d.noche]) {
      if (!pr?.hora) continue;
      const inicio = utcDesdeLocal(d.fecha, pr.hora, zonaHoraria(pr.spot.lon));
      // amanecer: desde 45 min antes; atardecer: desde 1 h antes; noche: 3 h desde la noche cerrada
      const antes = pr.momento === "amanecer" ? 45 : pr.momento === "atardecer" ? 60 : pr.momento === "luna" ? 30 : 0;
      const dur = pr.momento === "noche" ? 180 : 75;
      const ini = new Date(inicio.getTime() - antes * 60000);
      eventos.push({
        uid: `viaje-${d.fecha}-${pr.momento}-${pr.spot.id}@rasante`,
        titulo: `${TITULO[pr.momento]} · ${pr.spot.nombre}`,
        descripcion:
          (pr.nota !== undefined ? `Nota prevista ${pr.nota.toFixed(1)}. ` : "") +
          (pr.ruta ? `Subiendo por ${pr.ruta.nombre}: sal a las ${pr.ruta.salida}. ` : "") +
          `${SITIO}/spot/${pr.spot.id}`,
        lugar: [pr.spot.nombre, pr.spot.provincia].filter(Boolean).join(", "),
        geo: { lat: pr.spot.lat, lon: pr.spot.lon },
        url: `${SITIO}/spot/${pr.spot.id}`,
        inicio: ini,
        fin: new Date(ini.getTime() + dur * 60000),
      });
    }
    if (d.ruta) {
      eventos.push({
        uid: `viaje-${d.fecha}-ruta-${d.ruta.id}@rasante`,
        titulo: `Ruta: ${d.ruta.nombre}`,
        descripcion: `${d.ruta.km} km, +${d.ruta.subida} m. ${SITIO}/ruta/${d.ruta.id}`,
        dia: d.fecha,
        url: `${SITIO}/ruta/${d.ruta.id}`,
      });
    }
  }
  return new Response(calendario("Rasante · viaje", "Plan de viaje de fotografía y senderismo", eventos), {
    headers: {
      "Content-Type": "text/calendar; charset=utf-8",
      "Content-Disposition": `attachment; filename="rasante-viaje-${desde}.ics"`,
    },
  });
}
