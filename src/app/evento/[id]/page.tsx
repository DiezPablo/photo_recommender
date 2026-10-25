import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import BarraAnual from "@/features/eventos/componentes/BarraAnual";
import MapaEventos from "@/features/eventos/componentes/MapaEventos";
import ClimaSpot from "@/features/clima/componentes/ClimaSpot";
import FaunaCerca from "@/features/fauna/componentes/FaunaCerca";
import MarcaSendero from "@/features/rutas/componentes/MarcaSendero";
import { duracion } from "@/features/rutas/modelo";
import {
  cargarEventos,
  fechaCorta,
  fechaLarga,
  getEvento,
  MESES,
  mesDe,
  proximaTemporada,
  rutasCerca,
  spotsCerca,
} from "@/features/eventos/datos";

type Props = { params: Promise<{ id: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return (cargarEventos()?.naturaleza ?? []).map((e) => ({ id: e.id }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const e = getEvento((await params).id);
  if (!e) return {};
  return {
    title: e.nombre,
    description: `${e.descripcion} Habitualmente del ${fechaCorta(e.desde)} al ${fechaCorta(e.hasta)}.`,
  };
}

export default async function PaginaEvento({ params }: Props) {
  const eventos = cargarEventos();
  const e = getEvento((await params).id);
  if (!eventos || !e) notFound();
  const hoy = eventos.desde;
  const temporada = proximaTemporada(e, hoy);
  const lunasNuevas = eventos.luna.filter(
    (l) => l.fase === "nueva" && l.fecha >= temporada.desde && l.fecha <= temporada.hasta,
  );
  const spots = spotsCerca(e);
  const rutas = rutasCerca(e);

  return (
    <main className={`ficha evento cat-${e.categoria}`}>
      <nav className="migas rotulo" aria-label="Migas">
        <Link href="/calendario">Calendario</Link>
        <Link href={`/calendario/${MESES[mesDe(e.pico)]}`}>{MESES[mesDe(e.pico)]}</Link>
      </nav>
      <header className="ficha-cab">
        <p className={`rotulo cat-${e.categoria}`}>
          <span className="punto-cat" aria-hidden /> {eventos.categorias[e.categoria]} · {e.lugar}
          {e.provincia && ` (${e.provincia})`}
        </p>
        <h1>{e.nombre}</h1>
        <p className="entradilla">{e.descripcion}</p>
        <div className="temporada">
          <p>
            {temporada.ahora ? (
              <>
                <b>Ahora mismo</b>, hasta el {fechaLarga(temporada.hasta)}
              </>
            ) : (
              <>
                <b>Próxima temporada:</b> del {fechaLarga(temporada.desde, false)} al {fechaLarga(temporada.hasta)}
              </>
            )}
            . Mejor hacia el {fechaCorta(e.pico)}.
          </p>
          <BarraAnual evento={e} mesActual={Number(hoy.slice(5, 7)) - 1} />
        </div>
      </header>

      <div className="ficha-grid">
        <section className="seccion">
          <h2 className="rotulo">Dónde</h2>
          <MapaEventos
            eventos={[
              { id: e.id, nombre: e.nombre, lat: e.lat, lon: e.lon, radio_km: e.radio_km, categoria: e.categoria },
            ]}
            spots={spots}
            rutas={rutas.map((r) => ({ id: r.id, nombre: r.nombre, lat: r.lat, lon: r.lon }))}
            etiqueta={`Mapa de ${e.nombre}`}
          />
          <p className="leyenda-mapa">
            <span>
              <i className="leyenda-area" /> zona, unos {e.radio_km} km alrededor
            </span>
            {spots.length > 0 && (
              <span>
                <i className="leyenda-spot" /> spots
              </span>
            )}
            {rutas.length > 0 && (
              <span>
                <i className="salida-ruta" /> salida de rutas
              </span>
            )}
          </p>
        </section>
        <section className="seccion">
          <h2 className="rotulo">Para la foto</h2>
          <p>{e.consejo}</p>
          {lunasNuevas.length > 0 && (
            <p>
              Noches más oscuras de la temporada (luna nueva):{" "}
              {lunasNuevas.map((l) => fechaLarga(l.fecha, false)).join(", ")}.
            </p>
          )}
          <p className="nota-pie">
            Las fechas son las habituales y cambian cada año con el tiempo. Confirma antes de ir con el espacio natural
            o la oficina de turismo, respeta los accesos y no salgas de los caminos con la fauna.
          </p>
        </section>
      </div>

      <ClimaSpot lat={e.lat} lon={e.lon} mes={mesDe(e.pico)} titulo="El tiempo habitual en la zona" />

      <FaunaCerca
        lat={e.lat}
        lon={e.lon}
        km={e.radio_km + 10}
        max={e.categoria === "fauna" ? 6 : 3}
        titulo="Observatorios de fauna en la zona"
      />

      {spots.length > 0 && (
        <section className="seccion">
          <h2 className="rotulo">Spots en la zona</h2>
          <ul className="lista-cercanos">
            {spots.map((s) => (
              <li key={s.id}>
                <Link href={`/spot/${s.id}`}>{s.nombre}</Link>
                <small>
                  {s.tipo ? `${s.tipo} · ` : ""}a {Math.round(s.km)} km
                </small>
              </li>
            ))}
          </ul>
        </section>
      )}

      {rutas.length > 0 && (
        <section className="seccion">
          <h2 className="rotulo">Rutas en la zona</h2>
          <ul className="lista-cercanos">
            {rutas.map((r) => (
              <li key={r.id}>
                <MarcaSendero tipo={r.tipo} /> <Link href={`/ruta/${r.id}`}>{r.nombre}</Link>
                <small>
                  {r.km.toLocaleString("es-ES")} km · +{r.subida} m · {duracion(r.horas)} · {r.dificultad}
                </small>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
