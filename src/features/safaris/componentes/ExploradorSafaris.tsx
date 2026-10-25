"use client";
// Buscador de todos los parques del mundo (public/datos/safaris_indice.json, unos miles): texto, mes,
// continente y especie, con los filtros en la URL. Primero los que están en buena época ese mes y, dentro,
// los de más fauna observada.
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import MapaEventos from "@/features/eventos/componentes/MapaEventos";
import { MESES } from "@/features/eventos/modelo";
import { buenaEpoca, CONTINENTES, type FilaIndice } from "@/features/safaris/modelo";
import { useParametrosUrl } from "@/lib/almacen";

const POR_PAGINA = 30;
const EN_MAPA = 300;

function normal(t: string) {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

export default function ExploradorSafaris({
  especies,
  mesHoy,
  fotos,
}: {
  /** especies estrella: clave de GBIF y nombre */
  especies: { clave: number; nombre: string }[];
  mesHoy: number;
  /** fotos de los destacados (del catálogo curado), por id */
  fotos: Record<string, string>;
}) {
  const [filas, setFilas] = useState<FilaIndice[] | null>(null);
  const [error, setError] = useState(false);
  const [limite, setLimite] = useState(POR_PAGINA);
  const [parametros, actualizar] = useParametrosUrl();
  const texto = parametros.get("q") ?? "";
  const continente = parametros.get("continente") ?? "";
  const especie = parametros.get("especie") ?? "";
  const soloEpoca = parametros.get("epoca") === "1";
  const mes = parametros.has("mes") ? Number(parametros.get("mes")) : mesHoy;

  useEffect(() => {
    fetch("/datos/safaris_indice.json")
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => setFilas(d.parques))
      .catch(() => setError(true));
  }, []);

  const lista = useMemo(() => {
    if (!filas) return [];
    const q = normal(texto.trim());
    const clave = especie ? Number(especie) : null;
    return filas
      .map((f) => ({ f, epoca: buenaEpoca(f)?.includes(mes + 1) ?? false }))
      .filter(
        ({ f, epoca }) =>
          (!continente || f.c === continente) &&
          (clave === null || f.e.includes(clave)) &&
          (!soloEpoca || epoca) &&
          (!q || normal(`${f.n} ${f.p ?? ""}`).includes(q)),
      )
      .sort((a, b) => Number(b.epoca) - Number(a.epoca) || Number(b.f.d) - Number(a.f.d) || b.f.s - a.f.s);
  }, [filas, texto, continente, especie, soloEpoca, mes]);

  const puntos = useMemo(
    () =>
      lista.slice(0, EN_MAPA).map(({ f }) => ({
        id: f.id,
        nombre: `${f.n}${f.p ? ` (${f.p})` : ""}`,
        lat: f.la,
        lon: f.lo,
        radio_km: f.r,
        categoria: "fauna",
      })),
    [lista],
  );

  return (
    <div className="explorador-safaris">
      <div className="seccion filtros-fauna" role="search">
        <label className="campo">
          <span className="rotulo">Buscar</span>
          <input
            type="search"
            value={texto}
            onChange={(e) => {
              actualizar({ q: e.target.value });
              setLimite(POR_PAGINA);
            }}
            placeholder="Parque o país: Serengeti, Botsuana, Borneo, Yellowstone…"
          />
        </label>
        <div className="campos">
          <label className="campo">
            <span className="rotulo">Cuándo vas</span>
            <select value={mes} onChange={(e) => actualizar({ mes: e.target.value })}>
              {MESES.map((m, i) => (
                <option key={m} value={i}>
                  {m}
                  {i === mesHoy ? " (este mes)" : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="campo">
            <span className="rotulo">Continente</span>
            <select value={continente} onChange={(e) => actualizar({ continente: e.target.value })}>
              <option value="">Todo el mundo</option>
              {CONTINENTES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <label className="campo">
            <span className="rotulo">Qué quieres ver</span>
            <select value={especie} onChange={(e) => actualizar({ especie: e.target.value })}>
              <option value="">Cualquier especie</option>
              {especies.map((e) => (
                <option key={e.clave} value={e.clave}>
                  {e.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="campo campo-casilla">
            <input
              type="checkbox"
              checked={soloEpoca}
              onChange={(e) => actualizar({ epoca: e.target.checked ? "1" : null })}
            />
            <span>Solo los que están en buena época</span>
          </label>
        </div>
      </div>

      <div className="fauna-grid">
        <section className="seccion">
          <h2 className="rotulo" aria-live="polite">
            {filas
              ? `${lista.length.toLocaleString("es-ES")} parques · primero los que están en buena época en ${MESES[mes]}`
              : error
                ? "No se pudieron cargar los parques"
                : "Cargando parques…"}
          </h2>
          <ul className="rejilla-especies rejilla-safaris">
            {lista.slice(0, limite).map(({ f, epoca }) => (
              <li key={f.id} className="tarjeta-especie">
                {(f.f ?? fotos[f.id]) ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={f.f ?? fotos[f.id]} alt="" loading="lazy" decoding="async" />
                ) : (
                  <span className="sin-foto" aria-hidden />
                )}
                <div>
                  <h3>
                    <Link href={`/safaris/${f.id}`}>{f.n}</Link>
                  </h3>
                  <p className="meta">
                    {f.p ?? "—"} · {f.m >= 200 ? "200+" : f.m} especies de mamíferos
                    {f.d && " · destacado"}
                  </p>
                  <p className={epoca ? "en-temporada" : "fuera-temporada"}>
                    {epoca
                      ? `Buena época en ${MESES[mes]}`
                      : buenaEpoca(f)
                        ? "Mejor en otra época"
                        : "Sin temporada marcada"}
                  </p>
                </div>
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
          <MapaEventos eventos={puntos} enlace="/safaris" etiqueta="Mapa de parques de safari" mundo />
          {lista.length > EN_MAPA && <p className="nota-pie">En el mapa, los {EN_MAPA} primeros de la lista.</p>}
        </div>
      </div>
    </div>
  );
}
