import type { Metadata } from "next";
import BotonCercaViaje from "@/features/viaje/componentes/BotonCercaViaje";
import TarjetaDia from "@/features/viaje/componentes/TarjetaDia";
import { comunidades, MAX_DIAS, planificar, zonaDesdeParametros } from "@/features/viaje/plan";
import { fechaLocal } from "@/lib/sol";

export const metadata: Metadata = {
  title: "Planifica tu viaje",
  description:
    "Elige zona y fechas: qué fotografiar cada día al amanecer, al atardecer y de noche, qué ruta hacer y a qué hora salir.",
};

// Depende de los parámetros (zona y fechas): se genera en cada petición con los datos del último despliegue
export const dynamic = "force-dynamic";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

export default async function PaginaViaje({ searchParams }: Props) {
  const p = await searchParams;
  const v = (k: string) => (Array.isArray(p[k]) ? p[k][0] : p[k]);
  const hoy = fechaLocal(new Date());
  const desde = /^\d{4}-\d{2}-\d{2}$/.test(v("desde") ?? "") && v("desde")! >= hoy ? v("desde")! : hoy;
  const dias = Math.min(MAX_DIAS, Math.max(1, Number(v("dias")) || 3));
  const zona = zonaDesdeParametros(p);
  const pedido = !!(v("zona") || v("lat"));
  const plan = pedido ? planificar(zona, desde, dias) : null;
  const ccaa = comunidades();
  const consulta = new URLSearchParams(
    Object.entries({
      zona: zona.zona,
      desde,
      dias: String(dias),
      ...(zona.cerca ? { lat: String(zona.cerca.lat), lon: String(zona.cerca.lon), km: String(zona.cerca.km) } : {}),
    }),
  ).toString();

  return (
    <main className="calendario viaje">
      <header className="titular">
        <p className="rotulo">Planificador</p>
        <h1>Planifica tu viaje</h1>
        <p className="entradilla">
          Elige zona y fechas. Para los próximos cinco días, la previsión; más allá, lo habitual en esa época, la luna,
          el calendario de la naturaleza y las alineaciones.
        </p>
      </header>

      <form className="seccion form-viaje" method="get" action="/viaje">
        <label className="campo">
          <span className="rotulo">Zona</span>
          <select name="zona" defaultValue={zona.cerca ? "espana" : zona.zona}>
            <option value="espana">Toda España</option>
            {ccaa.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="campo">
          <span className="rotulo">Desde</span>
          <input type="date" name="desde" defaultValue={desde} min={hoy} />
        </label>
        <label className="campo">
          <span className="rotulo">Días</span>
          <select name="dias" defaultValue={String(dias)}>
            {Array.from({ length: MAX_DIAS }, (_, i) => i + 1).map((n) => (
              <option key={n}>{n}</option>
            ))}
          </select>
        </label>
        <input type="hidden" name="lat" defaultValue={zona.cerca ? String(zona.cerca.lat) : ""} />
        <input type="hidden" name="lon" defaultValue={zona.cerca ? String(zona.cerca.lon) : ""} />
        <div className="acciones-viaje">
          <button type="submit" className="boton boton-principal">
            Planificar
          </button>
          <BotonCercaViaje />
        </div>
      </form>

      {plan && (
        <>
          <p className="resumen-viaje">
            {zona.cerca
              ? `A menos de ${zona.cerca.km} km de tu ubicación`
              : zona.zona === "espana"
                ? "Toda España"
                : ccaa.find((c) => c.slug === zona.zona)?.nombre}
            : {plan.spots.toLocaleString("es-ES")} spots.{" "}
            <a href={`/viaje/calendario.ics?${consulta}`} download>
              Añadir el plan a tu calendario (.ics)
            </a>
          </p>
          {plan.spots === 0 ? (
            <p>No hay spots en esa zona.</p>
          ) : (
            <div className="dias-viaje">
              {plan.dias.map((d) => (
                <TarjetaDia key={d.fecha} d={d} />
              ))}
            </div>
          )}
        </>
      )}
    </main>
  );
}
