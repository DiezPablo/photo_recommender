// Ficha de un parque del mundo que no está en el catálogo escrito a mano: todo sale de datos abiertos
// (Wikidata, GBIF, NASA, OurAirports, OpenStreetMap) y de iNaturalist en directo.
import Link from "next/link";
import MapaEventos from "@/features/eventos/componentes/MapaEventos";
import { INICIALES, MESES } from "@/features/eventos/modelo";
import { CincoGrandes, CombinaCon } from "@/features/safaris/componentes/ComplementosSafari";
import OrganizaViaje from "@/features/safaris/componentes/OrganizaViaje";
import VistoAhora from "@/features/safaris/componentes/VistoAhora";
import {
  buenaEpoca,
  CLASE,
  type Mundo,
  nombreEspecieMundo,
  type ParqueMundo,
  TEXTO_MOTIVO,
  urlWeb,
} from "@/features/safaris/modelo";

function Barras({ valores, clase, titulo }: { valores: number[]; clase?: string; titulo: (v: number) => string }) {
  const max = Math.max(1, ...valores);
  return (
    <>
      {valores.map((v, i) => (
        <span role="cell" key={i} title={`${MESES[i]}: ${titulo(v)}`} className={`barra-ano ${clase ?? ""}`}>
          <i style={{ height: `${Math.max(4, (v / max) * 100)}%` }} />
        </span>
      ))}
    </>
  );
}

export default function FichaMundo({
  p,
  mundo,
  mesHoy,
  conFicha,
}: {
  p: ParqueMundo;
  mundo: Mundo;
  mesHoy: number;
  /** nombre científico del catálogo → slug de su página de especie */
  conFicha: Record<string, string>;
}) {
  const pais = p.pais ? mundo.paises[p.pais] : undefined;
  const epoca = buenaEpoca({ la: p.lat, sec: p.meses_secos, ep: p.epoca?.meses });
  const motivo = p.epoca?.motivo ?? (epoca ? "estación seca" : null);
  const estrella = Object.entries(p.estrella)
    .filter(([, n]) => n >= 3)
    .sort((a, b) => b[1] - a[1]);
  const puntos = [
    { id: p.id, nombre: p.nombre, lat: p.lat, lon: p.lon, radio_km: p.radio_km, categoria: "fauna", href: null },
    ...(p.osm?.alojamientos ?? []).map((a) => ({
      id: a.osm ?? `${a.lat},${a.lon}`,
      nombre: `${a.nombre} (${a.tipo})`,
      lat: a.lat,
      lon: a.lon,
      radio_km: 0.3,
      categoria: "otono",
      href: urlWeb(a.web) ?? (a.osm ? `https://www.openstreetmap.org/${a.osm}` : null),
    })),
  ];
  return (
    <main className="ficha evento cat-fauna safari">
      <nav className="migas rotulo" aria-label="Migas">
        <Link href="/safaris">Safaris</Link>
        {pais?.continente && <span>{pais.continente}</span>}
        {pais?.nombre && <span>{pais.nombre}</span>}
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
            <span className="punto-cat" aria-hidden /> {CLASE[p.clase] ?? p.clase}
            {pais?.nombre && ` · ${pais.nombre}`}
          </p>
          <h1>{p.nombre}</h1>
          <p className="chips">
            {p.area_km2 && <span className="chip">{p.area_km2.toLocaleString("es-ES")} km²</span>}
            {p.iucn && <span className="chip">UICN: {p.iucn}</span>}
            {p.unesco && <span className="chip">Patrimonio Mundial</span>}
            <span className="chip">{p.n_mamiferos >= 200 ? "200+" : p.n_mamiferos} especies de mamíferos</span>
          </p>
          <p className="entradilla">
            {p.obs.toLocaleString("es-ES")} observaciones de mamíferos registradas desde 2010.
            {epoca && (
              <>
                {" "}
                Mejor época: {epoca.map((m) => MESES[m - 1]).join(", ")}
                {motivo && <small> ({TEXTO_MOTIVO[motivo].toLowerCase()})</small>}
                {epoca.includes(mesHoy + 1) && <b> · ahora es buena época</b>}.
              </>
            )}
          </p>
          <p className="enlaces">
            <a href="#organiza">Organiza tu viaje ↓</a>
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
          <h2 className="rotulo">Especies estrella que se ven aquí</h2>
          <p className="enlaces-especies">
            {estrella.map(([k, n]) => {
              const cientifico = mundo.estrella[k];
              const s = conFicha[cientifico];
              const texto = `${nombreEspecieMundo(mundo, k)} (${n.toLocaleString("es-ES")})`;
              return s ? (
                <Link key={k} href={`/safaris/especie/${s}`}>
                  {texto}
                </Link>
              ) : (
                <span key={k}>{texto}</span>
              );
            })}
          </p>
        </section>
      )}

      <div className="ficha-grid">
        <section className="seccion">
          <h2 className="rotulo">Cuándo ir</h2>
          <div className="ano-safari" role="table" aria-label="El año en el parque">
            <div role="row" className="fila-ano cabecera-ano">
              <span role="rowheader" />
              {INICIALES.map((m, i) => (
                <span role="columnheader" key={i} className={i === mesHoy ? "actual" : undefined}>
                  {m}
                </span>
              ))}
            </div>
            {epoca && (
              <div role="row" className="fila-ano">
                <span role="rowheader">Mejor época</span>
                {MESES.map((m, i) => (
                  <span role="cell" key={m} className={epoca.includes(i + 1) ? "temporada-si" : "temporada-no"} />
                ))}
              </div>
            )}
            <div role="row" className="fila-ano">
              <span role="rowheader">Mamíferos vistos</span>
              <Barras valores={p.meses} titulo={(v) => `${v} observaciones`} />
            </div>
            {p.lluvia_mm && (
              <div role="row" className="fila-ano">
                <span role="rowheader">Lluvia</span>
                <Barras valores={p.lluvia_mm} clase="lluvia" titulo={(v) => `${v} mm`} />
              </div>
            )}
          </div>
          <p className="nota-pie">
            Mamíferos vistos: observaciones de GBIF por mes (reflejan también cuándo va más gente). Lluvia: climatología
            de la NASA (POWER).
          </p>
        </section>
        <VistoAhora lat={p.lat} lon={p.lon} radioKm={p.radio_km} respaldo={[]} conFicha={[]} />
      </div>

      <section className="seccion">
        <h2 className="rotulo">Lo que más se ve</h2>
        <div className="grupos-safari">
          {(
            [
              ["Mamíferos", p.mamiferos],
              ["Aves", p.aves],
            ] as const
          ).map(([titulo, lista]) =>
            lista.length ? (
              <div key={titulo}>
                <h3>{titulo}</h3>
                <ol className="lista-especies-safari">
                  {lista.map(([k, n]) => (
                    <li key={k}>
                      <a href={`https://www.gbif.org/species/${k}`} target="_blank" rel="noopener">
                        {nombreEspecieMundo(mundo, k)}
                      </a>{" "}
                      <small>{n.toLocaleString("es-ES")}</small>
                    </li>
                  ))}
                </ol>
              </div>
            ) : null,
          )}
        </div>
        <p className="nota-pie">Especies con más observaciones en GBIF desde 2010 en unos {p.radio_km} km alrededor.</p>
      </section>

      <CincoGrandes p={p} mundo={mundo} />

      <OrganizaViaje p={p} pais={pais} nombre={p.nombre} />

      <CombinaCon p={p} mundo={mundo} nombre={p.nombre} />

      <section className="seccion">
        <h2 className="rotulo">Mapa</h2>
        <MapaEventos eventos={puntos} etiqueta={`Mapa de ${p.nombre}`} mundo />
      </section>

      <p className="nota-pie">
        Fuentes:{" "}
        {Object.values(mundo.fuentes)
          .filter((f) => !f.startsWith("http"))
          .join(" · ")}
        . ¿Vas a organizarlo? Mira también <Link href="/safaris/guia">cómo elegir operador y lodge</Link>.
      </p>
    </main>
  );
}
