import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import EventosCerca from "@/features/eventos/componentes/EventosCerca";
import MapaEventos from "@/features/eventos/componentes/MapaEventos";
import { MESES } from "@/features/eventos/modelo";
import MesesFauna from "@/features/fauna/componentes/MesesFauna";
import { cargarFauna, getLugar, mesesBuenos, nombreEspecie, POCAS_OBSERVACIONES } from "@/features/fauna/datos";
import MarcaSendero from "@/features/rutas/componentes/MarcaSendero";
import { duracion, rutasQuePasan } from "@/features/rutas/datos";
import { fechaLocal } from "@/lib/sol";

type Props = { params: Promise<{ id: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return (cargarFauna()?.lugares ?? []).map((l) => ({ id: l.id }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const l = getLugar((await params).id);
  if (!l) return {};
  return {
    title: l.nombre,
    description: `Fauna en ${l.nombre} (${l.provincia}): ${l.especies.slice(0, 5).map(nombreEspecie).join(", ")}.`,
  };
}

export default async function PaginaLugarFauna({ params }: Props) {
  const l = getLugar((await params).id);
  if (!l) notFound();
  const fuentes = cargarFauna()?.fuentes ?? {};
  const max = Math.max(1, ...l.especies.map((e) => e.n));
  const buenos = mesesBuenos(l);
  const rutas = rutasQuePasan(l.lat, l.lon, 0.5)
    .filter((x) => x.paso.horasIda >= 1 / 6)
    .slice(0, 5);
  const mesHoy = Number(fechaLocal(new Date()).slice(5, 7)) - 1;
  return (
    <main className="ficha evento cat-fauna">
      <nav className="migas rotulo" aria-label="Migas">
        <Link href="/fauna">Fauna</Link>
        <span>{l.ccaa}</span>
        <span>{l.provincia}</span>
      </nav>
      <header className="ficha-cab">
        <p className="rotulo">
          <span className="punto-cat" aria-hidden /> Observación de fauna
          {l.observatorios > 1 && ` · ${l.observatorios} observatorios`}
          {l.accesible && " · accesible en silla de ruedas"}
        </p>
        <h1>{l.nombre}</h1>
        <p className="entradilla">
          {l.n_especies >= 300 ? "Más de 300" : l.n_especies} especies de aves y mamíferos registradas a unos 2 km entre
          2016 y 2025 ({l.observaciones.toLocaleString("es-ES")} observaciones).
          {buenos.length > 0 && <> Más actividad en {buenos.map((m) => MESES[m]).join(", ")}.</>}
        </p>
        <p className="enlaces">
          <a
            href={`https://www.google.com/maps/dir/?api=1&destination=${l.lat},${l.lon}`}
            target="_blank"
            rel="noopener"
          >
            Cómo llegar ↗
          </a>
          <a href={`https://www.openstreetmap.org/${l.osm}`} rel="noopener">
            En OpenStreetMap ↗
          </a>
        </p>
      </header>

      <div className="ficha-grid">
        <section className="seccion">
          <h2 className="rotulo">Lo que más se ve</h2>
          {l.observaciones < POCAS_OBSERVACIONES && (
            <p className="nota-pie">Hay pocas observaciones registradas aquí: la lista es orientativa.</p>
          )}
          <ol className="especies">
            {l.especies.map((e) => (
              <li key={`${e.cientifico}-${e.n}`}>
                <span className="barra-especie" style={{ width: `${(e.n / max) * 100}%` }} aria-hidden />
                <b>{nombreEspecie(e)}</b> {e.nombre && e.cientifico && <i>{e.cientifico}</i>}
                {e.clase === "mamifero" && <small> · mamífero</small>}
              </li>
            ))}
          </ol>
        </section>
        <section className="seccion">
          <h2 className="rotulo">Cuándo</h2>
          <MesesFauna meses={l.meses} mesActual={mesHoy} />
          <p className="nota-pie">
            Observaciones registradas por mes: reflejan la vida del lugar y también cuándo va más gente a mirar.
          </p>
          <MapaEventos
            eventos={[{ id: l.id, nombre: l.nombre, lat: l.lat, lon: l.lon, radio_km: 2, categoria: "fauna" }]}
            etiqueta={`Mapa de ${l.nombre}`}
          />
        </section>
      </div>

      {rutas.length > 0 && (
        <section className="seccion">
          <h2 className="rotulo">Rutas que pasan</h2>
          <ul className="lista-cercanos">
            {rutas.map(({ ruta: r, paso }) => (
              <li key={r.id}>
                <MarcaSendero tipo={r.tipo} /> <Link href={`/ruta/${r.id}`}>{r.nombre}</Link>
                <small>
                  km {paso.km.toLocaleString("es-ES")}, {duracion(paso.horasIda)} desde la salida · {r.dificultad}
                </small>
              </li>
            ))}
          </ul>
        </section>
      )}

      <EventosCerca lat={l.lat} lon={l.lon} ambito="fauna" />

      <p className="nota-pie">
        Lugares: {fuentes.lugares}. Observaciones: {fuentes.observaciones}. Las especies sensibles llegan con la
        ubicación generalizada. Respeta las distancias, el silencio y las épocas de cría.
      </p>
    </main>
  );
}
