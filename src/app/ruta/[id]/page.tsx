import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import BotonGpx from "@/components/BotonGpx";
import { Marca } from "@/components/ExploradorRutas";
import MapaRutas from "@/components/MapaRutas";
import PerfilRuta from "@/components/PerfilRuta";
import { cargarRutas, duracion, getRuta, slug } from "@/lib/rutas";

export const dynamicParams = false;

export function generateStaticParams() {
  const ids = cargarRutas().rutas.map((r) => ({ id: r.id }));
  return ids.length ? ids : [{ id: "sin-datos" }];
}

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const r = getRuta((await params).id);
  return r
    ? { title: r.nombre, description: `${r.nombre}: ${r.km} km, +${r.subida} m, ${duracion(r.horas)} (${r.provincia}). Trazado, perfil y GPX.` }
    : {};
}

const FUENTE: Record<string, string> = {
  osm: "OpenStreetMap",
  fedme: "Senderos homologados FEDME",
  mapa: "Caminos Naturales (MAPA)",
  "osm+fedme": "OpenStreetMap, con el nombre oficial de la FEDME",
  "osm+mapa": "OpenStreetMap, con el nombre oficial de Caminos Naturales",
};

const ATRIBUCION: Record<string, string> = {
  osm: "© colaboradores de OpenStreetMap (ODbL)",
  fedme: "Senderos FEDME (CC BY 4.0)",
  mapa: "Caminos Naturales © Ministerio de Agricultura, Pesca y Alimentación",
};

export default async function PaginaRuta({ params }: Props) {
  const r = getRuta((await params).id);
  if (!r) notFound();
  const atribucion = r.fuente.split("+").map((f) => ATRIBUCION[f]).filter(Boolean).join(" · ");
  const llegar = `https://www.google.com/maps/dir/?api=1&destination=${r.inicio[0]},${r.inicio[1]}`;
  return (
    <main className="ficha">
      <nav className="migas rotulo" aria-label="Migas">
        <Link href="/rutas">← Rutas</Link>
        <Link href={`/rutas/${slug(r.ccaa)}`}>{r.ccaa}</Link>
        <span>{r.provincia}</span>
      </nav>
      <header className="ficha-cab">
        <p className="rotulo tipo-ruta"><Marca tipo={r.tipo} /> {r.tipo}{r.ref ? ` · ${r.ref}` : ""}</p>
        <h1>{r.nombre}</h1>
        <dl className="ficha-datos">
          <div><dt>Distancia</dt><dd>{r.km.toLocaleString("es-ES")} km</dd></div>
          <div><dt>Desnivel</dt><dd>+{r.subida} / −{r.bajada} m</dd></div>
          <div title="Método MIDE: 4 km/h en llano, 400 m/h subiendo, 600 m/h bajando; sin paradas">
            <dt>Tiempo estimado</dt><dd>{duracion(r.horas)}</dd>
          </div>
          <div title="Estimación por tiempo, desnivel y altitud: no es la valoración MIDE oficial">
            <dt>Esfuerzo</dt><dd>{r.dificultad}</dd>
          </div>
          <div><dt>Recorrido</dt><dd>{r.circular ? "circular" : "lineal"}</dd></div>
          {r.alt_max !== null && <div><dt>Altitud</dt><dd>{r.alt_min}–{r.alt_max} m</dd></div>}
        </dl>
        <p className="enlaces">
          <a href={llegar} target="_blank" rel="noopener">Cómo llegar a la salida ↗</a>
          <BotonGpx nombre={r.nombre} linea={r.linea} fichero={slug(r.nombre) || r.id} atribucion={atribucion} />
          {r.oficial && <a href={r.oficial} target="_blank" rel="noopener">Ficha oficial ↗</a>}
          {r.web && r.web !== r.oficial && <a href={r.web} target="_blank" rel="noopener">Web de la ruta ↗</a>}
          {r.osm && <a href={`https://hiking.waymarkedtrails.org/#route?id=${r.osm}`} target="_blank" rel="noopener">Waymarked Trails ↗</a>}
          {r.osm && <a href={`https://www.openstreetmap.org/relation/${r.osm}`} target="_blank" rel="noopener">OpenStreetMap ↗</a>}
        </p>
      </header>

      <div className="ficha-grid">
        <section className="seccion">
          <h2 className="rotulo">Trazado</h2>
          <MapaRutas ruta={{ id: r.id, nombre: r.nombre, linea: r.linea, tipo: r.tipo }} alto="380px" />
          <p className="leyenda-mapa"><span><b className="marca-ruta salida">S</b> salida</span><span><b className="marca-ruta fin">F</b> llegada</span></p>
        </section>
        <section className="seccion">
          <h2 className="rotulo">Perfil</h2>
          <PerfilRuta perfil={r.perfil} nombre={r.nombre} />
          {(r.desde || r.hasta || r.operador || r.descripcion) && (
            <dl className="datos">
              {r.desde && (<><dt>Desde</dt><dd>{r.desde}</dd></>)}
              {r.hasta && (<><dt>Hasta</dt><dd>{r.hasta}</dd></>)}
              {r.operador && (<><dt>Gestiona</dt><dd>{r.operador}</dd></>)}
            </dl>
          )}
          {r.descripcion && <p className="descripcion">{r.descripcion}</p>}
        </section>
      </div>

      <section className="seccion">
        <h2 className="rotulo">Antes de salir</h2>
        <ul className="avisos-ruta">
          <li>Distancia, desnivel y tiempo se calculan con el trazado y un modelo del terreno: son orientativos. El
            tiempo no incluye paradas.</li>
          <li>No sabemos si el sendero está cortado, ni si hay restricciones de acceso o cupos (parques nacionales,
            época de cría): consulta la web del espacio protegido o del ayuntamiento.</li>
          <li>Mira la previsión de montaña (AEMET) y lleva el GPX descargado: en la sierra no siempre hay cobertura.</li>
        </ul>
        <p className="nota-pie">Fuente: {FUENTE[r.fuente] ?? r.fuente}. {atribucion}. Desnivel y perfil: teselas Terrarium (Mapzen/AWS).</p>
      </section>
    </main>
  );
}
