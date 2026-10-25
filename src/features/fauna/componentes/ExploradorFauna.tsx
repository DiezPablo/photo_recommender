"use client";
// Buscador de lugares de fauna: por lugar o especie, comunidad y mes. Los filtros viven en la URL
// (?q=&ccaa=&mes=). Carga public/datos/fauna.json una vez.
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import MapaEventos from "@/features/eventos/componentes/MapaEventos";
import { MESES } from "@/features/eventos/modelo";
import type { EspecieBreve } from "@/features/fauna/especies";
import { type Fauna, mesesBuenos, nombreEspecie } from "@/features/fauna/modelo";
import { useParametrosUrl } from "@/lib/almacen";

const POR_PAGINA = 40;

function normal(t: string) {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

export default function ExploradorFauna({
  comunidades,
  especies = [],
}: {
  comunidades: string[];
  /** especies con ficha propia: si la búsqueda coincide, se sugiere su página */
  especies?: EspecieBreve[];
}) {
  const [datos, setDatos] = useState<Fauna | null>(null);
  const [error, setError] = useState(false);
  const [parametros, actualizar] = useParametrosUrl();
  const texto = parametros.get("q") ?? "";
  const ccaa = parametros.get("ccaa") ?? "";
  const mes = parametros.get("mes") ?? "";
  const [limite, setLimite] = useState(POR_PAGINA);

  useEffect(() => {
    fetch("/datos/fauna.json")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setDatos)
      .catch(() => setError(true));
  }, []);

  const lista = useMemo(() => {
    if (!datos) return [];
    const q = normal(texto.trim());
    const m = mes === "" ? null : Number(mes);
    return datos.lugares.filter(
      (l) =>
        (!ccaa || l.ccaa === ccaa) &&
        (m === null || mesesBuenos(l).includes(m)) &&
        (!q ||
          normal(`${l.nombre} ${l.provincia}`).includes(q) ||
          l.especies.some((e) => normal(`${e.nombre ?? ""} ${e.cientifico ?? ""}`).includes(q))),
    );
  }, [datos, texto, ccaa, mes]);

  const sugeridas = useMemo(() => {
    const q = normal(texto.trim());
    return q.length < 3 ? [] : especies.filter((e) => normal(`${e.nombre} ${e.cientifico}`).includes(q));
  }, [especies, texto]);

  const puntos = useMemo(
    () => lista.map((l) => ({ id: l.id, nombre: l.nombre, lat: l.lat, lon: l.lon, radio_km: 2, categoria: "fauna" })),
    [lista],
  );

  return (
    <div className="explorador-fauna">
      <div className="seccion filtros-fauna" role="search">
        <label className="campo">
          <span className="rotulo">Buscar</span>
          <input
            type="search"
            value={texto}
            onChange={(e) => actualizar({ q: e.target.value })}
            placeholder="Lugar o especie: grulla, flamenco, Doñana…"
          />
        </label>
        <div className="campos">
          <label className="campo">
            <span className="rotulo">Comunidad</span>
            <select value={ccaa} onChange={(e) => actualizar({ ccaa: e.target.value })}>
              <option value="">Toda España</option>
              {comunidades.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <label className="campo">
            <span className="rotulo">Buen mes</span>
            <select value={mes} onChange={(e) => actualizar({ mes: e.target.value })}>
              <option value="">Cualquiera</option>
              {MESES.map((m, i) => (
                <option key={m} value={i}>
                  {m}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {sugeridas.length > 0 && (
        <p className="sugerencia-especie">
          {sugeridas.slice(0, 3).map((e) => (
            <Link key={e.id} href={`/fauna/especies/${e.id}`}>
              Dónde y cuándo ver: <b>{e.nombre}</b> →
            </Link>
          ))}
        </p>
      )}

      <div className="fauna-grid">
        <section className="seccion">
          <h2 className="rotulo" aria-live="polite">
            {datos
              ? `${lista.length.toLocaleString("es-ES")} lugares`
              : error
                ? "No se pudieron cargar los lugares"
                : "Cargando lugares…"}
          </h2>
          <ul className="lista-cercanos lista-fauna">
            {lista.slice(0, limite).map((l) => (
              <li key={l.id}>
                <Link href={`/fauna/${l.id}`}>{l.nombre}</Link>
                <small>
                  {l.provincia} · {l.n_especies >= 300 ? "más de 300" : l.n_especies} especies
                  {l.observatorios > 1 && ` · ${l.observatorios} observatorios`}
                </small>
                <small>{l.especies.slice(0, 4).map(nombreEspecie).join(", ")}</small>
              </li>
            ))}
          </ul>
          {lista.length > limite && (
            <button type="button" className="boton" onClick={() => setLimite(limite + POR_PAGINA)}>
              Ver más ({(lista.length - limite).toLocaleString("es-ES")})
            </button>
          )}
        </section>
        <div className="seccion mapa-mes">
          <MapaEventos eventos={puntos} enlace="/fauna" etiqueta="Mapa de lugares de fauna" />
        </div>
      </div>
    </div>
  );
}
