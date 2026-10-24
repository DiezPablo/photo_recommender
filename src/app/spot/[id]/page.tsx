import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import Cifra from "@/components/Cifra";
import Desglose from "@/components/Desglose";
import PlanDelDia from "@/components/PlanDelDia";
import MapaSpot from "@/components/MapaSpot";
import { filasRanking, TOP_HTML } from "@/lib/ranking";
import Panorama from "@/components/Panorama";
import type { LineaMapa } from "@/components/Mapa";
import {
  calificacion, type Dia, etiquetaDia, getSpot, horaDe, MESES_LARGOS, miniatura, MOMENTOS, NOMBRE_CORTO, rumbo,
  type Spot, TEXTO_AVISO, tramoTexto,
} from "@/lib/datos";

// 1500 fichas prerenderizadas ocupaban ~800 MB, cerca del límite de 1 GB de Vercel: se prerenderizan solo
// las más vistas (las del ranking de hoy) y el resto se genera al visitarlas (ISR) y queda en caché hasta
// el siguiente despliegue, que llega con cada actualización de datos.
export const dynamicParams = true;
export const revalidate = false;

export function generateStaticParams() {
  return filasRanking(0, "todos").slice(0, TOP_HTML).map((f) => ({ id: f.id }));
}

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const s = getSpot((await params).id);
  return s ? { title: s.nombre, description: `Condiciones para fotografía en ${s.nombre}: luz, nubes, luna, Vía Láctea y niebla.` } : {};
}

const CARDINALES: Record<string, number> = {
  N: 0, NNE: 22.5, NE: 45, ENE: 67.5, E: 90, ESE: 112.5, SE: 135, SSE: 157.5,
  S: 180, SSW: 202.5, SW: 225, WSW: 247.5, W: 270, WNW: 292.5, NW: 315, NNW: 337.5,
};

/** direction de OSM: "270", "W", "200-340"… → azimut central (o null). */
function azimutVista(d: string | null | undefined): number | null {
  if (!d) return null;
  const t = d.trim().toUpperCase();
  if (t in CARDINALES) return CARDINALES[t];
  const rango = t.match(/^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$/);
  if (rango) {
    const a = Number(rango[1]);
    let b = Number(rango[2]);
    if (b < a) b += 360;
    return ((a + b) / 2) % 360;
  }
  const n = Number(t);
  return Number.isFinite(n) ? n % 360 : null;
}

const pct = (v: number | null | undefined) => (v === null || v === undefined ? "—" : `${Math.round(v)} %`);

function Nubes({ m }: { m: NonNullable<Dia["meteo"]["amanecer"]> }) {
  const capas: [string, number][] = [
    ["Altas", m.nubes_altas], ["Medias", m.nubes_medias], ["Bajas", m.nubes_bajas], ["Horizonte*", m.nubes_horizonte],
  ];
  return (
    <div className="nubes-capas" aria-label="Nubes por capas">
      {capas.map(([k, v]) => (
        <div key={k}>
          <span>{k}</span>
          <span className="pista"><i style={{ width: `${v}%` }} /></span>
          <span style={{ textAlign: "right" }}>{v} %</span>
        </div>
      ))}
    </div>
  );
}

function BloqueLuz({ dia, momento }: { dia: Dia; momento: "amanecer" | "atardecer" }) {
  const m = dia.meteo[momento];
  const s = dia.sol;
  const am = momento === "amanecer";
  return (
    <div className="panel">
      <h3 className="rotulo">{am ? "Amanecer" : "Atardecer"}</h3>
      <dl className="datos">
        <dt>{am ? "Salida del sol" : "Puesta del sol"}</dt>
        <dd>{am ? s.amanecer : s.atardecer}</dd>
        {(am ? s.amanecer_relieve : s.atardecer_relieve) && (am ? s.amanecer_relieve : s.atardecer_relieve) !== (am ? s.amanecer : s.atardecer) && (
          <>
            <dt>{am ? "Asoma sobre el relieve" : "Se esconde tras el relieve"}</dt>
            <dd>{am ? s.amanecer_relieve : s.atardecer_relieve} ({am ? s.relieve_amanecer : s.relieve_atardecer}°)</dd>
          </>
        )}
        <dt>Hora azul</dt>
        <dd>{tramoTexto(am ? s.azul_manana : s.azul_tarde)}</dd>
        <dt>Hora dorada</dt>
        <dd>{tramoTexto(am ? s.dorada_manana : s.dorada_tarde)}</dd>
        <dt>Azimut del sol</dt>
        <dd>{rumbo(am ? s.az_amanecer : s.az_atardecer)}</dd>
        {m && (
          <>
            <dt>Visibilidad</dt>
            <dd>{m.visibilidad_km} km</dd>
            <dt>Prob. de lluvia</dt>
            <dd>{m.lluvia} %</dd>
            <dt>Viento · temperatura</dt>
            <dd>{m.viento} km/h · {m.temperatura} °C</dd>
          </>
        )}
      </dl>
      {m && <Nubes m={m} />}
    </div>
  );
}

function BloqueNoche({ dia, spot }: { dia: Dia; spot: Spot }) {
  const n = dia.noche;
  const vl = n.via_lactea;
  const mn = dia.meteo.noche;
  const lp = spot.contaminacion;
  return (
    <>
      <div className="panel">
        <h3 className="rotulo">Luna y oscuridad</h3>
        <dl className="datos">
          <dt>Noche astronómica</dt>
          <dd>{n.ini ? `${n.ini}–${n.fin}` : "no hay"}</dd>
          <dt>Fase</dt>
          <dd>{n.luna.fase} · {n.luna.iluminacion} %</dd>
          <dt>Salida · puesta</dt>
          <dd>{n.luna.salida ?? "—"} · {n.luna.puesta ?? "—"}</dd>
          {n.luna.evento && (
            <>
              <dt>{n.luna.evento.tipo === "salida" ? "Asoma sobre el paisaje" : "Se oculta tras el paisaje"}</dt>
              <dd>{n.luna.evento.hora} hacia {rumbo(n.luna.evento.azimut)} (sol a {n.luna.evento.altura_sol}°)</dd>
            </>
          )}
          <dt>Noche sin luna</dt>
          <dd>
            {n.luna.sin_luna.length ? n.luna.sin_luna.map((t) => tramoTexto(t)).join(", ") : "ninguna"}
            {n.luna.horas_sin_luna ? ` (${n.luna.horas_sin_luna} h)` : ""}
          </dd>
          {lp && (
            <>
              <dt>Contaminación lumínica</dt>
              <dd>≈ Bortle {lp.bortle} · {lp.sqm.toFixed(2)} mag/″² · {lp.descripcion}</dd>
            </>
          )}
        </dl>
      </div>
      <div className="panel">
        <h3 className="rotulo">Vía Láctea y meteo nocturna</h3>
        <dl className="datos">
          {(() => {
            const v = dia.notas.astro?.modelo?.ventana as [string, string] | undefined;
            return v ? (<><dt>Mejor ventana de 3 h</dt><dd>{v[0]}–{v[1]}</dd></>) : null;
          })()}
          <dt>Núcleo sobre 10°</dt>
          <dd>{vl.tramos.length ? vl.tramos.map((t) => tramoTexto(t)).join(", ") : "no sale de noche"}</dd>
          {vl.altura_max !== null && (
            <>
              <dt>Altura máxima</dt>
              <dd>{vl.altura_max}° a las {vl.hora_max} ({rumbo(vl.azimut_max)})</dd>
              <dt>Fotografiable sin luna</dt>
              <dd>{vl.horas_sin_luna ? `${vl.horas_sin_luna} h` : "no"}</dd>
            </>
          )}
          {mn && (
            <>
              <dt>Nubosidad</dt>
              <dd>{pct(mn.nubes)}</dd>
              <dt>Humedad</dt>
              <dd>{pct(mn.humedad)}</dd>
              <dt>Temp. mínima · punto de rocío</dt>
              <dd>{mn.temp_min ?? "—"} °C · {mn.punto_rocio ?? "—"} °C</dd>
              <dt>Viento · rachas</dt>
              <dd>{mn.viento} km/h · {mn.rachas ?? "—"} km/h</dd>
              {mn.vapor_mm != null && (<><dt>Vapor de agua (columna)</dt><dd>{mn.vapor_mm} mm</dd></>)}
              {mn.aod != null && (<><dt>Aerosoles (AOD)</dt><dd>{mn.aod}</dd></>)}
              {mn.cupula && (<><dt>Cúpula de luz</dt><dd>zona {mn.cupula.zona} a {mn.cupula.km} km hacia {mn.cupula.hacia ?? "el sur"}</dd></>)}
            </>
          )}
        </dl>
      </div>
    </>
  );
}

function BloqueDia({ dia, indice, spot }: { dia: Dia; indice: number; spot: Spot }) {
  const et = etiquetaDia(dia.fecha, indice);
  return (
    <details className="dia" open={indice === 0} id={`dia-${indice}`}>
      <summary>
        <h2>{et.corto === et.largo.slice(0, 3) ? et.largo : `${et.corto} · ${et.largo}`}</h2>
        <span className="mini-notas">
          {MOMENTOS.map((m) => {
            const n = dia.notas[m];
            return n ? (
              <span key={m} title={`${NOMBRE_CORTO[m]}: ${n.nota}`}>
                <small>{NOMBRE_CORTO[m]}</small> <Cifra nota={n.nota} />
              </span>
            ) : null;
          })}
        </span>
        {dia.fiabilidad !== "alta" && <span className={`fiabilidad ${dia.fiabilidad}`}>fiabilidad {dia.fiabilidad}</span>}
      </summary>
      <div className="dia-cuerpo">
        {dia.avisos.length > 0 && (
          <div className="avisos">{dia.avisos.map((a) => <span key={a} className="aviso">{TEXTO_AVISO[a] ?? a}</span>)}</div>
        )}
        <div className="notas-grid">
          {MOMENTOS.map((m) => {
            const n = dia.notas[m];
            return n ? <Desglose key={m} momento={m} n={n} subtitulo={horaDe(dia, m)} id={indice === 0 ? `nota-${m}` : undefined} /> : null;
          })}
        </div>
        <div className="datos-grid">
          <BloqueLuz dia={dia} momento="amanecer" />
          <BloqueLuz dia={dia} momento="atardecer" />
          <BloqueNoche dia={dia} spot={spot} />
        </div>
        <p className="nota-pie">
          * Horizonte: máximo de nubes bajas en el camino del sol (a 15, 40, 80 y 150 km en su dirección). Si hay un
          banco de nubes allí, el sol no llega a iluminar el cielo desde abajo.
        </p>
      </div>
    </details>
  );
}

export default async function PaginaSpot({ params }: Props) {
  const spot = getSpot((await params).id);
  if (!spot) notFound();
  const desc = spot.descubierto;
  const hoy = spot.dias[0];
  const vista = azimutVista(desc?.direccion_vista);
  const lineas: LineaMapa[] = [];
  if (hoy?.sol.az_amanecer != null) lineas.push({ azimut: hoy.sol.az_amanecer, km: 6, color: "var(--sol)", etiqueta: `Salida del sol (${rumbo(hoy.sol.az_amanecer)})` });
  if (hoy?.sol.az_atardecer != null) lineas.push({ azimut: hoy.sol.az_atardecer, km: 6, color: "var(--acento)", etiqueta: `Puesta del sol (${rumbo(hoy.sol.az_atardecer)})` });
  if (hoy?.noche.via_lactea.azimut_max != null) lineas.push({ azimut: hoy.noche.via_lactea.azimut_max, km: 4, color: "var(--vl)", etiqueta: "Núcleo de la Vía Láctea en su punto más alto", discontinua: true });
  if (vista !== null) lineas.push({ azimut: vista, km: 3, color: "var(--texto-2)", etiqueta: "Orientación de la vista (OSM)", discontinua: true });
  const portada = desc?.galeria?.[0] ?? null;
  const provincia = spot.provincia ?? desc?.provincia;
  const ccaa = spot.ccaa ?? desc?.ccaa;
  const maxMes = Math.max(...(desc?.meses ?? [0]), 1);
  const gmaps = `https://www.google.com/maps/dir/?api=1&destination=${spot.lat},${spot.lon}`;
  // Google no deja usar sus fotos gratis ni guardarlas (la API de Places es de pago): enlace a su ficha
  const gmapsVer = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(spot.nombre)}%20${spot.lat},${spot.lon}`;
  const osmRuta = `https://www.openstreetmap.org/directions?to=${spot.lat}%2C${spot.lon}#map=13/${spot.lat}/${spot.lon}`;

  return (
    <main className="ficha">
      <nav className="migas rotulo" aria-label="Migas">
        <Link href="/">← Ranking</Link>
        {provincia && <span>{provincia}</span>}
        {ccaa && <span>{ccaa}</span>}
      </nav>
      <header className="ficha-cab">
        <h1>{spot.nombre}</h1>
        <dl className="ficha-datos">
          {spot.tipo && (<div><dt>Tipo</dt><dd>{spot.tipo}</dd></div>)}
          {spot.elevacion !== null && (<div><dt>Altitud</dt><dd>{spot.elevacion} m</dd></div>)}
          {spot.contaminacion && (
            <div title={`Zona ${spot.contaminacion.zona} del atlas de D. Lorenz (brillo en el cénit); Bortle es una equivalencia aproximada`}>
              <dt>Cielo</dt><dd>Bortle ≈{spot.contaminacion.bortle} · {spot.contaminacion.sqm.toFixed(2)}</dd>
            </div>
          )}
          {vista !== null && (<div><dt>Vista</dt><dd>{rumbo(vista)}</dd></div>)}
          {desc && desc.fotografos > 0 && (<div><dt>En Commons</dt><dd>{desc.fotos} fotos · {desc.fotografos} autores</dd></div>)}
          {spot.origen === "osm" && (<div><dt>Fuente</dt><dd>Mirador de OpenStreetMap</dd></div>)}
          {spot.origen === "propio" && (<div><dt>Fuente</dt><dd>Spot propio</dd></div>)}
        </dl>
        <p className="enlaces">
          <a href={gmaps} target="_blank" rel="noopener">Cómo llegar ↗</a>
          <a href={gmapsVer} target="_blank" rel="noopener">Fotos en Google Maps ↗</a>
          <a href={osmRuta} target="_blank" rel="noopener">Ruta en OpenStreetMap ↗</a>
        </p>
      </header>

      {portada && (
        <figure className="foto-tira grande">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={miniatura(portada.url, 960) ?? portada.url} alt={portada.titulo || spot.nombre} fetchPriority="high" />
          <figcaption>
            Foto: <a href={portada.enlace} target="_blank" rel="noopener">{portada.autor}</a> · {portada.licencia || "Wikimedia Commons"}
            {portada.fecha ? ` · ${portada.fecha.slice(0, 4)}` : ""}
          </figcaption>
        </figure>
      )}

      {hoy && (
        <section className="lectura" aria-label="Notas de hoy">
          <h2 className="rotulo">Hoy</h2>
          <ol>
            {MOMENTOS.map((m) => hoy.notas[m] ? (
              <li key={m}>
                <a href={`#nota-${m}`}>
                  <span className="rotulo">{NOMBRE_CORTO[m]}</span>
                  <Cifra nota={hoy.notas[m]!.nota} className="grande" />
                  <span className={`medidor ${calificacion(hoy.notas[m]!.nota).clase}`}><i style={{ width: `${hoy.notas[m]!.nota * 10}%` }} /></span>
                  <small>{horaDe(hoy, m)}</small>
                </a>
              </li>
            ) : null)}
          </ol>
        </section>
      )}

      {hoy && <PlanDelDia dia={hoy} />}

      <div className="ficha-grid">
        <section>
          <MapaSpot punto={{ id: spot.id, nombre: spot.nombre, lat: spot.lat, lon: spot.lon, clase: "n-top" }} lineas={lineas} />
          <div className="leyenda-mapa">
            <span><i style={{ background: "var(--sol)" }} />Salida del sol {rumbo(hoy?.sol.az_amanecer)}</span>
            <span><i style={{ background: "var(--acento)" }} />Puesta {rumbo(hoy?.sol.az_atardecer)}</span>
            {hoy?.noche.via_lactea.azimut_max != null && <span><i style={{ background: "var(--vl)" }} />Vía Láctea</span>}
            {vista !== null && <span><i style={{ background: "var(--texto-2)" }} />Vista (OSM)</span>}
          </div>
        </section>
        <section className="seccion">
          <h2 className="rotulo">Lo que fotografía la gente</h2>
          {desc && desc.galeria.length > 0 ? (
            <div className="galeria">
              {desc.galeria.map((f) => (
                <figure key={f.url}>
                  <a href={f.enlace} target="_blank" rel="noopener">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={f.url} alt={f.titulo || `Foto de ${spot.nombre}`} loading="lazy" width={320} height={240} />
                  </a>
                  <figcaption>
                    © <a href={f.enlace} target="_blank" rel="noopener">{f.autor}</a> · {f.licencia || "ver licencia"}
                    {f.fecha ? ` · ${f.fecha.slice(0, 4)}` : ""}
                  </figcaption>
                </figure>
              ))}
            </div>
          ) : (
            <p style={{ margin: 0, color: "var(--texto-2)" }}>No hay fotos de este punto en Wikimedia Commons.</p>
          )}
          {desc && desc.meses.some((m) => m > 0) && (
            <div style={{ marginTop: 14 }}>
              <h3 style={{ fontSize: "0.9rem", marginBottom: 6 }}>
                Meses más fotografiados: {desc.meses_top.map((m) => MESES_LARGOS[m - 1]).join(", ")}
              </h3>
              <div className="meses" aria-hidden="true">
                {desc.meses.map((v, i) => <div key={i} style={{ height: `${(v / maxMes) * 100}%` }} title={`${MESES_LARGOS[i]}: ${v}`} />)}
              </div>
              <div className="meses-et" aria-hidden="true">{"EFMAMJJASOND".split("").map((l, i) => <span key={i}>{l}</span>)}</div>
              {(desc.pct_amanecer > 0 || desc.pct_atardecer > 0 || desc.pct_noche > 0) && (
                <p style={{ margin: "8px 0 0", fontSize: "0.82rem", color: "var(--texto-2)" }}>
                  Fotos con hora conocida: {desc.pct_amanecer} % al amanecer, {desc.pct_atardecer} % al atardecer,{" "}
                  {desc.pct_noche} % de noche.
                </p>
              )}
            </div>
          )}
        </section>
      </div>

      {desc?.horizonte?.angulos?.length ? (
        <section className="seccion" aria-label="Horizonte del terreno">
          <h2 className="rotulo">Horizonte y orientación</h2>
          <Panorama
            angulos={desc.horizonte.angulos}
            marcas={[
              ...(hoy?.sol.az_amanecer != null ? [{ azimut: hoy.sol.az_amanecer, texto: `Sale el sol ${hoy.sol.amanecer_relieve ?? hoy.sol.amanecer}`, color: "var(--sol)" }] : []),
              ...(hoy?.sol.az_atardecer != null ? [{ azimut: hoy.sol.az_atardecer, texto: `Se pone ${hoy.sol.atardecer_relieve ?? hoy.sol.atardecer}`, color: "var(--acento)" }] : []),
              ...(hoy?.noche.luna.evento ? [{ azimut: hoy.noche.luna.evento.azimut, texto: `Luna ${hoy.noche.luna.evento.hora}`, color: "var(--luna)", altura: hoy.noche.luna.evento.horizonte }] : []),
              ...(hoy?.noche.via_lactea.azimut_max != null ? [{ azimut: hoy.noche.via_lactea.azimut_max, texto: `Vía Láctea ${hoy.noche.via_lactea.hora_max}`, color: "var(--vl)", altura: hoy.noche.via_lactea.altura_max ?? undefined }] : []),
            ]}
          />
        </section>
      ) : null}

      <section className="dias" aria-label="Previsión por días">
        <h2 className="rotulo">Previsión día a día · el desglose suma exactamente la nota</h2>
        {spot.dias.map((d, i) => <BloqueDia key={d.fecha} dia={d} indice={i} spot={spot} />)}
      </section>
    </main>
  );
}
