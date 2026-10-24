"use client";
// Buscador de rutas: descarga el índice compacto (JSON estático) y filtra en el navegador por texto,
// comunidad, tipo, distancia, dificultad, circular y cercanía. Sin JavaScript, la página enlaza a los
// listados por comunidad.
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { DIFICULTADES, duracion, type FilaRuta, RANGOS_KM, TIPOS_RUTA, type TipoRuta } from "@/lib/modeloRutas";
import { distanciaKm, guardarUbicacion, leerUbicacion, type Ubicacion } from "@/lib/ubicacion";
import MapaRutas from "./MapaRutas";

const POR_PAGINA = 50;
const RADIOS = [0, 10, 25, 50, 100];

function normal(t: string) {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

export function Marca({ tipo }: { tipo: TipoRuta }) {
  return <span className={`marca-sendero t-${normal(tipo).replace(/[^a-z]+/g, "-")}`} title={tipo} aria-hidden="true" />;
}

export default function ExploradorRutas({ comunidades }: { comunidades: string[] }) {
  const [todas, setTodas] = useState<FilaRuta[] | null>(null);
  const [error, setError] = useState(false);
  const [texto, setTexto] = useState("");
  const [ccaa, setCcaa] = useState("");
  const [tipos, setTipos] = useState<Set<TipoRuta>>(new Set());
  const [rango, setRango] = useState("");
  const [dif, setDif] = useState("");
  const [circular, setCircular] = useState(false);
  const [orden, setOrden] = useState<"destacadas" | "cerca" | "km" | "subida" | "nombre">("destacadas");
  const [ubic, setUbic] = useState<Ubicacion | null>(null);
  const [radio, setRadio] = useState(0);
  const [limite, setLimite] = useState(POR_PAGINA);
  const [estado, setEstado] = useState("");

  const [listoUrl, setListoUrl] = useState(false);

  // Filtros en la URL (?q=&ccaa=&tipo=&km=&dif=&circular=1&orden=): al volver desde una ruta siguen ahí y
  // una búsqueda se puede compartir. Se lee al cargar y se escribe con replaceState (sin recargar).
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    if (p.get("q")) setTexto(p.get("q")!);
    if (p.get("ccaa")) setCcaa(p.get("ccaa")!);
    if (p.get("tipo")) setTipos(new Set(p.get("tipo")!.split(",").filter((t) => TIPOS_RUTA.includes(t as TipoRuta)) as TipoRuta[]));
    if (p.get("km")) setRango(p.get("km")!);
    if (p.get("dif")) setDif(p.get("dif")!);
    if (p.get("circular")) setCircular(true);
    if (p.get("orden")) setOrden(p.get("orden") as typeof orden);
    setListoUrl(true);
  }, []);

  useEffect(() => {
    if (!listoUrl) return;
    const p = new URLSearchParams();
    if (texto.trim()) p.set("q", texto.trim());
    if (ccaa) p.set("ccaa", ccaa);
    if (tipos.size) p.set("tipo", [...tipos].join(","));
    if (rango) p.set("km", rango);
    if (dif) p.set("dif", dif);
    if (circular) p.set("circular", "1");
    if (orden !== "destacadas" && orden !== "cerca") p.set("orden", orden);
    const q = p.toString();
    window.history.replaceState(window.history.state, "", q ? `?${q}` : window.location.pathname);
  }, [listoUrl, texto, ccaa, tipos, rango, dif, circular, orden]);

  useEffect(() => {
    fetch("/datos-rutas/indice").then((r) => (r.ok ? r.json() : Promise.reject())).then(setTodas).catch(() => setError(true));
    const u = leerUbicacion();
    setUbic(u);
    if (u) {
      if (!new URLSearchParams(window.location.search).get("orden")) setOrden("cerca");
      setRadio(50);
    }
    try {
      if (!new URLSearchParams(window.location.search).get("ccaa")) setCcaa(localStorage.getItem("rutas-ccaa") ?? "");
    } catch {}
  }, []);

  function pedirUbicacion() {
    if (!navigator.geolocation) return setEstado("Tu navegador no da la ubicación");
    setEstado("Buscando tu ubicación…");
    navigator.geolocation.getCurrentPosition(
      (p) => {
        const u = { lat: +p.coords.latitude.toFixed(3), lon: +p.coords.longitude.toFixed(3) };
        guardarUbicacion(u);
        setUbic(u);
        setOrden("cerca");
        setRadio(50);
        setEstado("");
      },
      () => setEstado("No se pudo obtener la ubicación"),
      { maximumAge: 600000, timeout: 15000 },
    );
  }

  const filtradas = useMemo(() => {
    if (!todas) return [];
    const q = normal(texto.trim());
    const r = RANGOS_KM.find((x) => x.id === rango);
    const lista = todas
      .map((f) => ({ ...f, dist: ubic ? distanciaKm(ubic, f) : null }))
      .filter((f) =>
        (!q || normal(`${f.nombre} ${f.ref ?? ""} ${f.provincia}`).includes(q)) &&
        (!ccaa || f.ccaa === ccaa) && (!tipos.size || tipos.has(f.tipo)) &&
        (!r || (f.km >= r.min && f.km < r.max)) && (!dif || f.dificultad === dif) && (!circular || f.circular) &&
        (!radio || f.dist === null || f.dist <= radio));
    const cmp = {
      destacadas: (a: typeof lista[0], b: typeof lista[0]) => b.rel - a.rel || a.nombre.localeCompare(b.nombre, "es"),
      cerca: (a: typeof lista[0], b: typeof lista[0]) => (a.dist ?? 0) - (b.dist ?? 0),
      km: (a: typeof lista[0], b: typeof lista[0]) => a.km - b.km,
      subida: (a: typeof lista[0], b: typeof lista[0]) => b.subida - a.subida,
      nombre: (a: typeof lista[0], b: typeof lista[0]) => a.nombre.localeCompare(b.nombre, "es"),
    }[orden === "cerca" && !ubic ? "destacadas" : orden];
    return lista.sort(cmp);
  }, [todas, texto, ccaa, tipos, rango, dif, circular, radio, ubic, orden]);

  useEffect(() => setLimite(POR_PAGINA), [texto, ccaa, tipos, rango, dif, circular, radio, orden]);

  function alternarTipo(t: TipoRuta) {
    setTipos((s) => {
      const n = new Set(s);
      if (n.has(t)) n.delete(t);
      else n.add(t);
      return n;
    });
  }

  return (
    <div className="explorador">
      <div className="columna">
        <div className="filtros-rutas" role="search">
          <label className="campo">
            <span className="rotulo">Buscar</span>
            <input type="search" value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Nombre, PR-M 1, provincia…" />
          </label>
          <div className="campos">
            <label className="campo">
              <span className="rotulo">Comunidad</span>
              <select value={ccaa} onChange={(e) => { setCcaa(e.target.value); try { localStorage.setItem("rutas-ccaa", e.target.value); } catch {} }}>
                <option value="">Toda España</option>
                {comunidades.map((c) => <option key={c}>{c}</option>)}
              </select>
            </label>
            <label className="campo">
              <span className="rotulo">Distancia</span>
              <select value={rango} onChange={(e) => setRango(e.target.value)}>
                <option value="">Cualquiera</option>
                {RANGOS_KM.map((r) => <option key={r.id} value={r.id}>{r.texto}</option>)}
              </select>
            </label>
            <label className="campo">
              <span className="rotulo">Dificultad</span>
              <select value={dif} onChange={(e) => setDif(e.target.value)}>
                <option value="">Cualquiera</option>
                {DIFICULTADES.map((d) => <option key={d}>{d}</option>)}
              </select>
            </label>
            <label className="campo">
              <span className="rotulo">Ordenar</span>
              <select value={orden} onChange={(e) => setOrden(e.target.value as typeof orden)}>
                <option value="destacadas">Destacadas</option>
                {ubic && <option value="cerca">Más cerca</option>}
                <option value="nombre">Nombre</option>
                <option value="km">Más cortas</option>
                <option value="subida">Más desnivel</option>
              </select>
            </label>
          </div>
          <div className="tipos" role="group" aria-label="Tipo de sendero">
            {TIPOS_RUTA.map((t) => (
              <button key={t} type="button" aria-pressed={tipos.has(t)} onClick={() => alternarTipo(t)}>
                <Marca tipo={t} /> {t}
              </button>
            ))}
          </div>
          <div className="herramientas">
            <label className="casilla"><input type="checkbox" checked={circular} onChange={(e) => setCircular(e.target.checked)} /> Solo circulares</label>
            {ubic ? (
              <label>
                <span className="sr">Distancia a ti</span>
                <select className="boton" value={radio} onChange={(e) => setRadio(Number(e.target.value))}>
                  {RADIOS.map((r) => <option key={r} value={r}>{r ? `A menos de ${r} km de ti` : "A cualquier distancia"}</option>)}
                </select>
              </label>
            ) : (
              <button type="button" className="boton" onClick={pedirUbicacion}>Cerca de mí</button>
            )}
            {estado && <span role="status">{estado}</span>}
          </div>
        </div>

        <section className="bloque-ranking" aria-label="Rutas">
          <h2 className="rotulo" aria-live="polite">
            {todas ? `${filtradas.length.toLocaleString("es-ES")} rutas` : error ? "No se pudieron cargar las rutas" : "Cargando rutas…"}
          </h2>
          <ol className="lista-rutas">
            {filtradas.slice(0, limite).map((f) => (
              <li key={f.id}>
                <Link href={`/ruta/${f.id}`} className="fila-ruta">
                  <Marca tipo={f.tipo} />
                  <div>
                    <h3>{f.nombre}</h3>
                    <p className="meta">
                      {f.ref && <span>{f.ref}</span>}
                      <span>{f.km.toLocaleString("es-ES")} km</span>
                      <span>+{f.subida} m</span>
                      <span>{duracion(f.horas)}</span>
                      <span>{f.dificultad}</span>
                      {f.circular && <span>circular</span>}
                      <span>{f.provincia}</span>
                      {f.dist !== null && <span className="dist">a {f.dist < 10 ? f.dist.toFixed(1) : Math.round(f.dist)} km</span>}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ol>
          {filtradas.length > limite && (
            <button type="button" className="boton" onClick={() => setLimite((l) => l + POR_PAGINA)}>
              Ver más ({(filtradas.length - limite).toLocaleString("es-ES")})
            </button>
          )}
        </section>
      </div>
      <MapaRutas filas={filtradas} />
    </div>
  );
}
