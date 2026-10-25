import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import MapaEventos from "@/features/eventos/componentes/MapaEventos";
import { MESES } from "@/features/eventos/modelo";
import {
  cargarRecientes,
  cargarSafaris,
  getEspecieSafari,
  cargarMundo,
  getParque,
  nombreTaxon,
  parquesMundoDe,
  slugEspecie,
} from "@/features/safaris/datos";
import { fechaLocal } from "@/lib/sol";

type Props = { params: Promise<{ slug: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return (cargarSafaris()?.especies ?? []).map((e) => ({ slug: slugEspecie(e) }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const e = getEspecieSafari((await params).slug);
  if (!e) return {};
  return {
    title: `Dónde ver ${nombreTaxon(e).toLowerCase()}`,
    description: `Los mejores parques del mundo para ver ${nombreTaxon(e).toLowerCase()} (${e.cientifico}) y cuándo ir.`,
  };
}

export default async function PaginaEspecieSafari({ params }: Props) {
  const e = getEspecieSafari((await params).slug);
  if (!e) notFound();
  const recientes = cargarRecientes();
  const mesHoy = Number(fechaLocal(new Date()).slice(5, 7)) - 1;
  const parques = e.parques
    .map((x) => ({ ...x, p: getParque(x.id)!, mes: recientes?.parques[x.id]?.estrella[String(e.taxon)] ?? 0 }))
    .filter((x) => x.p);
  const max = Math.max(1, ...parques.map((x) => x.n));
  const destacados = new Set(parques.map((x) => x.id));
  const mundo = parquesMundoDe(e.cientifico).filter((x) => !destacados.has(x.p.id));
  const paises = cargarMundo()?.paises ?? {};
  return (
    <main className="ficha evento cat-fauna especie">
      <nav className="migas rotulo" aria-label="Migas">
        <Link href="/safaris">Safaris</Link>
        <Link href="/safaris/especie">Especies</Link>
      </nav>
      <header className="ficha-cab cabecera-especie">
        {e.foto && (
          <figure>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={e.foto.url.replace("/medium.", "/large.")} alt={nombreTaxon(e)} />
            <figcaption>{e.foto.autor} · iNaturalist</figcaption>
          </figure>
        )}
        <div>
          <p className="rotulo">
            <span className="punto-cat" aria-hidden /> <i>{e.cientifico}</i>
          </p>
          <h1>{nombreTaxon(e)}</h1>
          <p className="entradilla">
            {parques.length
              ? `Dónde más se ha observado entre los ${cargarSafaris()?.parques.length} parques de safari, con su mejor época.`
              : "Hay muy pocas observaciones en los parques de la lista."}
          </p>
        </div>
      </header>
      <div className="ficha-grid">
        <section className="seccion">
          <h2 className="rotulo">Mejores parques</h2>
          <ol className="zonas-especie">
            {parques.map((x) => (
              <li key={x.id}>
                <span className="barra-especie" style={{ width: `${(x.n / max) * 100}%` }} aria-hidden />
                <Link href={`/safaris/${x.id}`}>
                  <b>{x.p.nombre}</b>
                </Link>{" "}
                <small>
                  ({x.p.pais}) · {x.n.toLocaleString("es-ES")} observaciones
                  {x.mes > 0 && ` · ${x.mes} en el último mes`} · mejor en{" "}
                  {x.p.meses.length === 12 ? "todo el año" : x.p.meses.map((m) => MESES[m - 1]).join(", ")}
                  {x.p.meses.includes(mesHoy + 1) && " · ahora es buena época"}
                </small>
              </li>
            ))}
          </ol>
        </section>
        <section className="seccion">
          <MapaEventos
            eventos={parques.map((x) => ({
              id: x.id,
              nombre: x.p.nombre,
              lat: x.p.lat,
              lon: x.p.lon,
              radio_km: x.p.radio_km,
              categoria: "fauna",
            }))}
            enlace="/safaris"
            etiqueta={`Mapa de dónde ver ${nombreTaxon(e).toLowerCase()}`}
            mundo
          />
        </section>
      </div>
      {mundo.length > 0 && (
        <section className="seccion">
          <h2 className="rotulo">Más parques del mundo donde se ve</h2>
          <ul className="lista-cercanos">
            {mundo.map(({ p, n }) => (
              <li key={p.id}>
                <Link href={`/safaris/${p.id}`}>{p.nombre}</Link>
                <small>
                  {(p.pais && paises[p.pais]?.nombre) ?? "—"} · {n.toLocaleString("es-ES")} observaciones en GBIF
                </small>
              </li>
            ))}
          </ul>
        </section>
      )}
      <p className="nota-pie">
        Observaciones verificables de iNaturalist alrededor de cada parque: dependen también de cuánta gente va y sube
        fotos. Foto: {e.foto?.licencia}.
      </p>
    </main>
  );
}
