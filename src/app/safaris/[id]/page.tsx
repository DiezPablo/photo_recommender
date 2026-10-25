import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import MapaEventos from "@/features/eventos/componentes/MapaEventos";
import { MESES } from "@/features/eventos/modelo";
import AnoSafari from "@/features/safaris/componentes/AnoSafari";
import VistoAhora from "@/features/safaris/componentes/VistoAhora";
import {
  cargarRecientes,
  cargarSafaris,
  enlaceResenas,
  especiePorTaxon,
  getParque,
  nombreTaxon,
  slugEspecie,
  TEXTO_TIPO,
} from "@/features/safaris/datos";
import { fechaLocal } from "@/lib/sol";

type Props = { params: Promise<{ id: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return (cargarSafaris()?.parques ?? []).map((p) => ({ id: p.id }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const p = getParque((await params).id);
  if (!p) return {};
  return {
    title: `Safari en ${p.nombre}`,
    description: `${p.nombre} (${p.pais}): cuándo ir, qué se ve, tipos de safari, tasas y alojamientos. ${p.consejo}`,
  };
}

const GRUPOS: [string, string, number][] = [
  ["Mammalia", "Mamíferos", 15],
  ["Aves", "Aves", 8],
  ["Reptilia", "Reptiles", 5],
];

export default async function PaginaParque({ params }: Props) {
  const p = getParque((await params).id);
  if (!p) notFound();
  const datos = cargarSafaris()!;
  const recientes = cargarRecientes()?.parques[p.id];
  const mesHoy = Number(fechaLocal(new Date()).slice(5, 7)) - 1;
  const estrella = p.estrella.map(especiePorTaxon).filter((e) => e !== undefined);
  const conFicha = datos.especies.map((e) => e.taxon);
  const respaldo = (recientes?.mamiferos ?? []).map((m) => ({ ...m, foto: null }));
  const alojamientos = p.alojamientos ?? [];
  const puntos = [
    { id: p.id, nombre: p.nombre, lat: p.lat, lon: p.lon, radio_km: p.radio_km, categoria: "fauna", href: null },
    ...alojamientos.map((a) => ({
      id: a.osm,
      nombre: `${a.nombre} (${a.tipo})`,
      lat: a.lat,
      lon: a.lon,
      radio_km: 0.3,
      categoria: "otono",
      href: a.web ?? `https://www.openstreetmap.org/${a.osm}`,
    })),
  ];
  return (
    <main className="ficha evento cat-fauna safari">
      <nav className="migas rotulo" aria-label="Migas">
        <Link href="/safaris">Safaris</Link>
        <span>{p.continente}</span>
        <span>{p.pais}</span>
      </nav>
      <header className="ficha-cab cabecera-especie">
        {p.foto && (
          <figure>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={p.foto.url} alt={p.nombre} />
            <figcaption>
              {p.foto.web ? (
                <a href={p.foto.web} rel="noopener">
                  {p.foto.autor ?? "Wikimedia Commons"}
                </a>
              ) : (
                p.foto.autor
              )}
              {p.foto.licencia && ` · ${p.foto.licencia}`}
            </figcaption>
          </figure>
        )}
        <div>
          <p className="rotulo">
            <span className="punto-cat" aria-hidden /> {p.pais} · {p.continente}
          </p>
          <h1>{p.nombre}</h1>
          <p className="entradilla">{p.consejo}</p>
          <p className="chips">
            {p.tipos.map((t) => (
              <span key={t} className="chip">
                {TEXTO_TIPO[t] ?? t}
              </span>
            ))}
          </p>
          <p className="meta">
            Mejor época: {p.meses.length === 12 ? "todo el año" : p.meses.map((m) => MESES[m - 1]).join(", ")}
            {p.meses.includes(mesHoy + 1) && <b> · ahora es buena época</b>}
          </p>
          <p className="enlaces">
            {p.web && (
              <a href={p.web} target="_blank" rel="noopener">
                Web oficial ↗
              </a>
            )}
            {p.es && (
              <a href={p.es} target="_blank" rel="noopener">
                Wikipedia ↗
              </a>
            )}
            <a
              href={`https://www.inaturalist.org/observations?lat=${p.lat}&lng=${p.lon}&radius=${p.radio_km}`}
              target="_blank"
              rel="noopener"
            >
              Observaciones en iNaturalist ↗
            </a>
          </p>
        </div>
      </header>

      {estrella.length > 0 && (
        <section className="seccion">
          <h2 className="rotulo">Especies estrella</h2>
          <ul className="rejilla-especies rejilla-estrella">
            {estrella.map((e) => {
              const n = p.conteo_estrella?.[String(e.taxon)] ?? 0;
              const mes = recientes?.estrella[String(e.taxon)] ?? 0;
              return (
                <li key={e.taxon} className="tarjeta-especie">
                  {e.foto ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={e.foto.url} alt="" loading="lazy" />
                  ) : (
                    <span className="sin-foto" aria-hidden />
                  )}
                  <div>
                    <h3>
                      <Link href={`/safaris/especie/${slugEspecie(e)}`}>{nombreTaxon(e)}</Link>
                    </h3>
                    <p>
                      <i>{e.cientifico}</i>
                    </p>
                    <p className="meta">
                      {n.toLocaleString("es-ES")} observaciones aquí
                      {mes > 0 && ` · ${mes} en el último mes`}
                    </p>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <div className="ficha-grid">
        <section className="seccion">
          <h2 className="rotulo">Cuándo ir</h2>
          <AnoSafari p={p} mesActual={mesHoy} />
          <p className="nota-pie">
            Temporada: la recomendada para ver fauna. Mamíferos vistos: observaciones de iNaturalist por mes (reflejan
            también cuándo va más gente). Clima: medias de ERA5 de dos años.
          </p>
        </section>
        <VistoAhora lat={p.lat} lon={p.lon} radioKm={p.radio_km} respaldo={respaldo} conFicha={conFicha} />
      </div>

      {p.especies && (
        <section className="seccion">
          <h2 className="rotulo">Lo que más se ve</h2>
          <div className="grupos-safari">
            {GRUPOS.map(([g, titulo, max]) =>
              p.especies?.[g]?.length ? (
                <div key={g}>
                  <h3>{titulo}</h3>
                  <ol className="lista-especies-safari">
                    {p.especies[g].slice(0, max).map((e) => (
                      <li key={e.taxon}>
                        {conFicha.includes(e.taxon) ? (
                          <Link href={`/safaris/especie/${slugEspecie(e)}`}>{nombreTaxon(e)}</Link>
                        ) : (
                          nombreTaxon(e)
                        )}{" "}
                        <small>{e.n?.toLocaleString("es-ES")}</small>
                      </li>
                    ))}
                  </ol>
                </div>
              ) : null,
            )}
          </div>
          <p className="nota-pie">
            Especies con más observaciones verificadas en iNaturalist en unos {p.radio_km} km alrededor.
          </p>
        </section>
      )}

      <div className="ficha-grid">
        <section className="seccion">
          <h2 className="rotulo">Tasas y permisos</h2>
          <p>{p.tasa ?? "Las tasas cambian a menudo: consúltalas en la web oficial del parque antes de reservar."}</p>
          {p.tasa && <p className="nota-pie">Orientativo: comprueba la tarifa vigente en la web oficial.</p>}
          <h2 className="rotulo">Reservar</h2>
          <ul className="lista-reservar">
            <li>
              <b>Entrada y permisos:</b>{" "}
              {p.web ? (
                <a href={p.web} target="_blank" rel="noopener">
                  web oficial del parque ↗
                </a>
              ) : (
                "en la autoridad de parques del país"
              )}
              .
            </li>
            <li>
              <b>Alojamiento:</b> directamente con el lodge o campamento (abajo, con su web) suele salir igual o más
              barato que en una agencia y la comisión se queda en el destino.
            </li>
            <li>
              <b>Operador o guía:</b> mira <Link href="/safaris/guia#operador">cómo elegir un operador de safari</Link>.
            </li>
          </ul>
        </section>
        <section className="seccion">
          <h2 className="rotulo">Mapa</h2>
          <MapaEventos eventos={puntos} etiqueta={`Mapa de ${p.nombre}`} mundo />
        </section>
      </div>

      {alojamientos.length > 0 && (
        <section className="seccion">
          <h2 className="rotulo">Dónde dormir</h2>
          <ul className="lista-alojamientos">
            {alojamientos.map((a) => (
              <li key={a.osm}>
                <b>{a.nombre}</b> <small>{a.tipo}</small>
                <span className="enlaces">
                  {a.web && (
                    <a href={a.web} target="_blank" rel="noopener">
                      Web y reservas ↗
                    </a>
                  )}
                  {a.telefono && <a href={`tel:${a.telefono.split(";")[0]}`}>{a.telefono.split(";")[0]}</a>}
                  <a href={enlaceResenas(a)} target="_blank" rel="noopener">
                    Reseñas ↗
                  </a>
                </span>
              </li>
            ))}
          </ul>
          <p className="nota-pie">
            Lodges, campamentos y hoteles con nombre en OpenStreetMap dentro del parque o cerca. No cobramos comisión ni
            hay alojamientos patrocinados; las reseñas se abren en Google Maps.
          </p>
        </section>
      )}

      <p className="nota-pie">
        Fuentes: {Object.values(datos.fuentes).join(" · ")}. Respeta las distancias, no pidas al guía salirse de las
        pistas para acercarse a los animales y no hagas actividades con fauna en cautividad (paseos con leones,
        elefantes montados).
      </p>
    </main>
  );
}
