// «Organiza tu viaje»: datos reales de cada parque para planificarlo. Cómo llegar (aeropuertos y pistas de
// OurAirports), puertas de entrada, pueblos, operadores y alojamientos (OpenStreetMap), y enlaces oficiales.
import { enlaceResenas, type LugarOsm, type Pais, type ParqueMundo } from "@/features/safaris/modelo";

const EXTERIORES = "https://www.exteriores.gob.es/";

function Contacto({ l }: { l: LugarOsm }) {
  return (
    <span className="enlaces">
      {l.web && (
        <a href={l.web} target="_blank" rel="noopener">
          Web ↗
        </a>
      )}
      {l.telefono && <a href={`tel:${l.telefono}`}>{l.telefono}</a>}
      {l.email && <a href={`mailto:${l.email}`}>Correo</a>}
      <a href={enlaceResenas(l)} target="_blank" rel="noopener">
        Reseñas ↗
      </a>
    </span>
  );
}

export default function OrganizaViaje({
  p,
  pais,
  nombre,
  conAlojamientos = true,
}: {
  p: ParqueMundo;
  pais?: Pais;
  nombre: string;
  /** en los parques del catálogo los alojamientos ya salen en su propia sección */
  conAlojamientos?: boolean;
}) {
  const o = p.osm;
  const { aeropuertos, pistas, n_pistas } = p.llegar;
  return (
    <section className="seccion organiza" id="organiza">
      <h2 className="rotulo">Organiza tu viaje a {nombre}</h2>
      <div className="organiza-grid">
        <div>
          <h3>Cómo llegar</h3>
          <ul className="lista-organiza">
            {aeropuertos.map((a) => (
              <li key={a.iata}>
                <b>
                  {a.nombre} ({a.iata})
                </b>
                <small>
                  {a.internacional ? "gran aeropuerto internacional" : "vuelos regulares"}
                  {a.ciudad ? ` · ${a.ciudad}` : ""} · a {a.km} km en línea recta
                </small>
              </li>
            ))}
            {n_pistas > 0 && (
              <li>
                <b>
                  {n_pistas} {n_pistas === 1 ? "pista de aterrizaje" : "pistas de aterrizaje"} en la zona del parque (a
                  menos de {Math.round(p.radio_km + 5)} km del centro)
                </b>
                <small>
                  Para llegar en avioneta (vuelos chárter o regulares de safari); confirma con el lodge cuál le queda
                  cerca: {pistas.map((x) => `${x.nombre} (${x.km} km)`).join(", ")}
                </small>
              </li>
            )}
          </ul>
          {o && o.puertas.length > 0 && (
            <>
              <h3>Puertas de entrada</h3>
              <ul className="lista-organiza">
                {o.puertas.map((x) => (
                  <li key={`${x.lat},${x.lon}`}>
                    <a
                      href={`https://www.google.com/maps/dir/?api=1&destination=${x.lat},${x.lon}`}
                      target="_blank"
                      rel="noopener"
                    >
                      {x.nombre} ↗
                    </a>{" "}
                    <small>a {x.km} km del centro</small>
                  </li>
                ))}
              </ul>
            </>
          )}
          {o && o.pueblos.length > 0 && (
            <>
              <h3>Pueblos y ciudades cerca</h3>
              <p>{o.pueblos.map((x) => `${x.nombre} (${x.km} km)`).join(" · ")}</p>
            </>
          )}
        </div>
        <div>
          <h3>Antes de ir</h3>
          <ul className="lista-organiza">
            {pais?.nombre && (
              <li>
                <b>Visado, salud y seguridad:</b>{" "}
                <a href={EXTERIORES} target="_blank" rel="noopener">
                  Ministerio de Asuntos Exteriores ↗
                </a>{" "}
                (en «Recomendaciones de viaje», busca {pais.nombre})
              </li>
            )}
            {(pais?.moneda || pais?.idiomas.length) && (
              <li>
                {pais?.moneda && (
                  <>
                    <b>Moneda:</b> {pais.moneda}.{" "}
                  </>
                )}
                {pais?.idiomas.length ? (
                  <>
                    <b>Idiomas:</b> {pais.idiomas.join(", ")}.
                  </>
                ) : null}
              </li>
            )}
            {p.web && (
              <li>
                <b>Entradas y normas:</b>{" "}
                <a href={p.web} target="_blank" rel="noopener">
                  web oficial ↗
                </a>
              </li>
            )}
            {p.wdpa && (
              <li>
                <b>Ficha del espacio protegido:</b>{" "}
                <a href={`https://www.protectedplanet.net/${p.wdpa}`} target="_blank" rel="noopener">
                  Protected Planet ↗
                </a>
              </li>
            )}
            {p.wiki && (
              <li>
                <a href={p.wiki} target="_blank" rel="noopener">
                  Artículo en Wikipedia ↗
                </a>
              </li>
            )}
          </ul>
          {o && o.operadores.length > 0 && (
            <>
              <h3>Operadores y agencias de la zona</h3>
              <ul className="lista-organiza">
                {o.operadores.map((x) => (
                  <li key={x.osm}>
                    <b>{x.nombre}</b> <small>a {x.km} km</small>
                    <Contacto l={x} />
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>
      {conAlojamientos && o && o.alojamientos.length > 0 && (
        <>
          <h3>Dónde dormir</h3>
          <ul className="lista-alojamientos">
            {o.alojamientos.map((a) => (
              <li key={a.osm}>
                <b>{a.nombre}</b>{" "}
                <small>
                  {a.tipo} · a {a.km} km del centro
                </small>
                <Contacto l={a} />
              </li>
            ))}
          </ul>
        </>
      )}
      {!o && <p className="nota-pie">Los alojamientos, operadores y puertas de este parque se están recopilando.</p>}
      <p className="nota-pie">
        Aeropuertos de OurAirports; puertas, pueblos, operadores y alojamientos de OpenStreetMap: datos abiertos que
        pueden estar incompletos. Sin comisiones ni anuncios: reserva directamente y lee reseñas recientes.
      </p>
    </section>
  );
}
