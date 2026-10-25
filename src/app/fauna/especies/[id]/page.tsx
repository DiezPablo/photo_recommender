import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import MapaEventos from "@/features/eventos/componentes/MapaEventos";
import TarjetaEvento from "@/features/eventos/componentes/TarjetaEvento";
import { cargarEventos, getEvento, MESES } from "@/features/eventos/datos";
import MesesFauna from "@/features/fauna/componentes/MesesFauna";
import {
  cargarEspecies,
  faunaCerca,
  getEspecie,
  GRUPOS,
  lugaresConEspecie,
  mesesFaciles,
  provinciasDe,
  radioZona,
  resumirMeses,
} from "@/features/fauna/datos";
import { fechaLocal } from "@/lib/sol";

type Props = { params: Promise<{ id: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return (cargarEspecies()?.especies ?? []).map((e) => ({ id: e.id }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const e = getEspecie((await params).id);
  if (!e) return {};
  return {
    title: `Dónde ver ${e.nombre.toLowerCase()}`,
    description: `Dónde y cuándo ver ${e.nombre.toLowerCase()} (${e.cientifico}) en España: ${provinciasDe(e).join(", ")}.`,
  };
}

export default async function PaginaEspecie({ params }: Props) {
  const e = getEspecie((await params).id);
  if (!e) notFound();
  const fuentes = cargarEspecies()?.fuentes ?? {};
  const eventos = cargarEventos();
  const relacionados = e.eventos.map(getEvento).filter((x) => x !== undefined);
  const faciles = mesesFaciles(e);
  const mesHoy = Number(fechaLocal(new Date()).slice(5, 7)) - 1;
  const observatorios = lugaresConEspecie(e.cientifico);
  // el observatorio más cercano a cada zona, para tener un sitio concreto al que ir
  const zonas = e.zonas.map((z) => ({ ...z, cerca: faunaCerca(z.lat, z.lon, 30)[0] }));
  // en la lista, una línea por provincia (con varias zonas, la de más peso y el observatorio más cercano)
  const porProvincia = [...new Set(zonas.map((z) => z.provincia))].map((p) => {
    const suyas = zonas.filter((z) => z.provincia === p);
    const cerca = suyas
      .map((z) => z.cerca)
      .filter((c) => c !== undefined)
      .sort((a, b) => a.km - b.km)[0];
    return { ...suyas[0], n: suyas.length, cerca };
  });
  const puntos = [
    ...zonas.map((z, i) => ({
      id: `zona-${i}`,
      nombre: `${z.provincia}: zona con muchas observaciones`,
      lat: z.lat,
      lon: z.lon,
      radio_km: radioZona(z),
      categoria: "fauna",
      href: null,
    })),
    ...observatorios.map((l) => ({
      id: l.id,
      nombre: l.nombre,
      lat: l.lat,
      lon: l.lon,
      radio_km: 1,
      categoria: "fauna",
    })),
  ];
  return (
    <main className="ficha evento cat-fauna especie">
      <nav className="migas rotulo" aria-label="Migas">
        <Link href="/fauna">Fauna</Link>
        <Link href="/fauna/especies">Especies</Link>
        <span>{GRUPOS[e.grupo]}</span>
      </nav>
      <header className="ficha-cab cabecera-especie">
        {e.foto && (
          <figure>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={e.foto.url} alt={e.nombre} />
            <figcaption>
              {e.foto.web ? (
                <a href={e.foto.web} rel="noopener">
                  {e.foto.autor ?? "Wikimedia Commons"}
                </a>
              ) : (
                e.foto.autor
              )}
              {e.foto.licencia && ` · ${e.foto.licencia}`}
            </figcaption>
          </figure>
        )}
        <div>
          <p className="rotulo">
            <span className="punto-cat" aria-hidden /> {GRUPOS[e.grupo]} · <i>{e.cientifico}</i>
          </p>
          <h1>{e.nombre}</h1>
          <p className="entradilla">{e.consejo}</p>
          <p className="meta">
            {e.observaciones.toLocaleString("es-ES")} observaciones en España entre 2016 y 2025
            {faciles.length ? ` · más fácil de ${resumirMeses(faciles, MESES)}` : " · todo el año"}
          </p>
        </div>
      </header>

      <div className="ficha-grid">
        <section className="seccion">
          <h2 className="rotulo">Dónde se ha visto más</h2>
          {puntos.length > 0 ? (
            <MapaEventos eventos={puntos} enlace="/fauna" etiqueta={`Mapa de dónde ver ${e.nombre.toLowerCase()}`} />
          ) : (
            <p>Hay muy pocas observaciones con ubicación.</p>
          )}
          <ol className="zonas-especie">
            {porProvincia.map((z) => (
              <li key={z.provincia}>
                <span className="barra-especie" style={{ width: `${z.peso}%` }} aria-hidden />
                <b>{z.provincia}</b> <small>({z.ccaa})</small>
                {z.n > 1 && <small> · {z.n} zonas</small>}
                {z.cerca && (
                  <small>
                    {" "}
                    · cerca: <Link href={`/fauna/${z.cerca.id}`}>{z.cerca.nombre}</Link> ({Math.round(z.cerca.km)} km)
                  </small>
                )}
              </li>
            ))}
          </ol>
          <p className="nota-pie">
            Zonas de unos 25 km donde más se ha observado; dependen también de dónde hay más observadores.
          </p>
        </section>
        <section className="seccion">
          <h2 className="rotulo">Cuándo</h2>
          <MesesFauna meses={e.meses} mesActual={mesHoy} relativo />
          <p className="nota-pie">
            Observaciones de cada mes frente a todas las de {e.grupo === "ave" ? "aves" : "mamíferos"} de ese mes: así
            no pesa que en primavera sale más gente al campo.
          </p>
          {observatorios.length > 0 && (
            <>
              <h2 className="rotulo">Observatorios donde se ve</h2>
              <ul className="lista-cercanos">
                {observatorios.map((l) => (
                  <li key={l.id}>
                    <Link href={`/fauna/${l.id}`}>{l.nombre}</Link>
                    <small>
                      {l.provincia} · {l.nEspecie.toLocaleString("es-ES")} observaciones a ~2 km
                    </small>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      </div>

      {eventos && relacionados.length > 0 && (
        <section className="seccion">
          <h2 className="rotulo">En el calendario</h2>
          <div className="rejilla-eventos">
            {relacionados.map((ev) => (
              <TarjetaEvento key={ev.id} evento={ev} categorias={eventos.categorias} />
            ))}
          </div>
        </section>
      )}

      <p className="nota-pie">
        Observaciones: {fuentes.observaciones}. Foto: {fuentes.fotos}. Las especies sensibles llegan con la ubicación
        generalizada y aquí solo se muestran zonas de ~25 km. Respeta las distancias, no uses reclamos ni cebos y no
        difundas la ubicación de nidos o madrigueras.
      </p>
    </main>
  );
}
