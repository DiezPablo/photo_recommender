"use client";
// Buscador de rutas: descarga el índice compacto (JSON estático) y filtra en el navegador por texto,
// comunidad, tipo, distancia, dificultad, circular y cercanía. Los filtros viven en la URL
// (?q=&ccaa=&tipo=&km=&dif=&circular=1&orden=): al volver desde una ruta siguen ahí y una búsqueda se
// puede compartir. Sin JavaScript, la página enlaza a los listados por comunidad.
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import MapaRutas from "@/features/rutas/componentes/MapaRutas";
import MarcaSendero from "@/features/rutas/componentes/MarcaSendero";
import { DIFICULTADES, duracion, type FilaRuta, RANGOS_KM, TIPOS_RUTA, type TipoRuta } from "@/features/rutas/modelo";
import { leerAlmacen, useParametrosUrl, usePreferenciaNumero } from "@/lib/almacen";
import { distanciaKm, pedirUbicacion, useUbicacion } from "@/lib/ubicacion";

const POR_PAGINA = 50;
const RADIOS = [0, 10, 25, 50, 100];
const ORDENES = ["destacadas", "cerca", "nombre", "km", "subida"] as const;
type Orden = (typeof ORDENES)[number];

/** Texto sin tildes y en minúsculas, para buscar sin importar cómo se escriba. */
function normal(t: string) {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

export default function ExploradorRutas({ comunidades }: { comunidades: string[] }) {
  const [todas, setTodas] = useState<FilaRuta[] | null>(null);
  const [error, setError] = useState(false);
  const [estado, setEstado] = useState("");
  const [radio, setRadio] = usePreferenciaNumero("rutas-radio", 50);
  const ubic = useUbicacion();

  // Filtros: la URL es la única fuente de verdad
  const [parametros, actualizar] = useParametrosUrl();
  const texto = parametros.get("q") ?? "";
  const ccaa = parametros.get("ccaa") ?? "";
  const rango = parametros.get("km") ?? "";
  const dif = parametros.get("dif") ?? "";
  const circular = parametros.get("circular") === "1";
  const tipos = useMemo(
    () =>
      new Set(
        (parametros.get("tipo") ?? "").split(",").filter((t): t is TipoRuta => TIPOS_RUTA.includes(t as TipoRuta)),
      ),
    [parametros],
  );
  const pedido = parametros.get("orden") as Orden | null;
  const orden: Orden = pedido && ORDENES.includes(pedido) ? pedido : ubic ? "cerca" : "destacadas";

  // Paginación: vuelve a la primera página cuando cambia cualquier filtro
  const firma = `${parametros.toString()}|${radio}|${ubic ? 1 : 0}`;
  const [pagina, setPagina] = useState({ firma, limite: POR_PAGINA });
  const limite = pagina.firma === firma ? pagina.limite : POR_PAGINA;

  useEffect(() => {
    fetch("/datos-rutas/indice")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setTodas)
      .catch(() => setError(true));
    // la comunidad elegida la última vez, si la URL no trae filtros
    const guardada = leerAlmacen("rutas-ccaa");
    if (guardada && !window.location.search) actualizar({ ccaa: guardada });
  }, [actualizar]);

  async function buscarUbicacion() {
    setEstado("Buscando tu ubicación…");
    const r = await pedirUbicacion();
    if (!r.ok) return setEstado(r.error);
    setRadio(50);
    actualizar({ orden: null }); // con ubicación, el orden por defecto es «más cerca»
    setEstado("");
  }

  function cambiarCcaa(c: string) {
    actualizar({ ccaa: c });
    try {
      localStorage.setItem("rutas-ccaa", c);
    } catch {}
  }

  function alternarTipo(t: TipoRuta) {
    const n = new Set(tipos);
    if (n.has(t)) n.delete(t);
    else n.add(t);
    actualizar({ tipo: [...n].join(",") });
  }

  const filtradas = useMemo(() => {
    if (!todas) return [];
    const q = normal(texto.trim());
    const r = RANGOS_KM.find((x) => x.id === rango);
    const lista = todas
      .map((f) => ({ ...f, dist: ubic ? distanciaKm(ubic, f) : null }))
      .filter(
        (f) =>
          (!q || normal(`${f.nombre} ${f.ref ?? ""} ${f.provincia}`).includes(q)) &&
          (!ccaa || f.ccaa === ccaa) &&
          (!tipos.size || tipos.has(f.tipo)) &&
          (!r || (f.km >= r.min && f.km < r.max)) &&
          (!dif || f.dificultad === dif) &&
          (!circular || f.circular) &&
          (!radio || f.dist === null || f.dist <= radio),
      );
    type F = (typeof lista)[number];
    const comparar: Record<Orden, (a: F, b: F) => number> = {
      destacadas: (a, b) => b.rel - a.rel || a.nombre.localeCompare(b.nombre, "es"),
      cerca: (a, b) => (a.dist ?? 0) - (b.dist ?? 0),
      km: (a, b) => a.km - b.km,
      subida: (a, b) => b.subida - a.subida,
      nombre: (a, b) => a.nombre.localeCompare(b.nombre, "es"),
    };
    return lista.sort(comparar[orden === "cerca" && !ubic ? "destacadas" : orden]);
  }, [todas, texto, ccaa, tipos, rango, dif, circular, radio, ubic, orden]);

  return (
    <div className="explorador">
      <div className="columna">
        <div className="filtros-rutas" role="search">
          <label className="campo">
            <span className="rotulo">Buscar</span>
            <input
              type="search"
              value={texto}
              onChange={(e) => actualizar({ q: e.target.value })}
              placeholder="Nombre, PR-M 1, provincia…"
            />
          </label>
          <div className="campos">
            <label className="campo">
              <span className="rotulo">Comunidad</span>
              <select value={ccaa} onChange={(e) => cambiarCcaa(e.target.value)}>
                <option value="">Toda España</option>
                {comunidades.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            <label className="campo">
              <span className="rotulo">Distancia</span>
              <select value={rango} onChange={(e) => actualizar({ km: e.target.value })}>
                <option value="">Cualquiera</option>
                {RANGOS_KM.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.texto}
                  </option>
                ))}
              </select>
            </label>
            <label className="campo">
              <span className="rotulo">Dificultad</span>
              <select value={dif} onChange={(e) => actualizar({ dif: e.target.value })}>
                <option value="">Cualquiera</option>
                {DIFICULTADES.map((d) => (
                  <option key={d}>{d}</option>
                ))}
              </select>
            </label>
            <label className="campo">
              <span className="rotulo">Ordenar</span>
              <select value={orden} onChange={(e) => actualizar({ orden: e.target.value })}>
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
                <MarcaSendero tipo={t} /> {t}
              </button>
            ))}
          </div>
          <div className="herramientas">
            <label className="casilla">
              <input
                type="checkbox"
                checked={circular}
                onChange={(e) => actualizar({ circular: e.target.checked ? "1" : null })}
              />{" "}
              Solo circulares
            </label>
            {ubic ? (
              <label>
                <span className="sr">Distancia a ti</span>
                <select className="boton" value={radio} onChange={(e) => setRadio(Number(e.target.value))}>
                  {RADIOS.map((r) => (
                    <option key={r} value={r}>
                      {r ? `A menos de ${r} km de ti` : "A cualquier distancia"}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <button type="button" className="boton" onClick={buscarUbicacion}>
                Cerca de mí
              </button>
            )}
            {estado && (
              <span role="status" className="estado-ubic">
                {estado}
              </span>
            )}
          </div>
        </div>

        <section className="bloque-ranking" aria-label="Rutas">
          <h2 className="rotulo" aria-live="polite">
            {todas
              ? `${filtradas.length.toLocaleString("es-ES")} rutas`
              : error
                ? "No se pudieron cargar las rutas"
                : "Cargando rutas…"}
          </h2>
          <ol className="lista-rutas">
            {filtradas.slice(0, limite).map((f) => (
              <li key={f.id}>
                <Link href={`/ruta/${f.id}`} className="fila-ruta">
                  <MarcaSendero tipo={f.tipo} />
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
                      {f.dist !== null && (
                        <span className="dist">a {f.dist < 10 ? f.dist.toFixed(1) : Math.round(f.dist)} km</span>
                      )}
                    </p>
                  </div>
                </Link>
              </li>
            ))}
          </ol>
          {filtradas.length > limite && (
            <button type="button" className="boton" onClick={() => setPagina({ firma, limite: limite + POR_PAGINA })}>
              Ver más ({(filtradas.length - limite).toLocaleString("es-ES")})
            </button>
          )}
        </section>
      </div>
      <MapaRutas filas={filtradas} />
    </div>
  );
}
