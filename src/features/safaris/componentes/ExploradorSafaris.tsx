"use client";
// Buscador de parques de safari: continente, mes, tipo de safari y especie (filtros en la URL). Ordena por
// «mejor en ese mes»: primero los parques en temporada y, entre ellos, los que más especies estrella tienen.
import Link from "next/link";
import { useMemo } from "react";
import MapaEventos from "@/features/eventos/componentes/MapaEventos";
import { MESES } from "@/features/eventos/modelo";
import {
  CONTINENTES,
  enTemporada,
  type Parque,
  puntuacionAhora,
  type Recientes,
  TEXTO_TIPO,
} from "@/features/safaris/modelo";
import { useParametrosUrl } from "@/lib/almacen";

export type ParqueBreve = Pick<
  Parque,
  | "id"
  | "nombre"
  | "pais"
  | "continente"
  | "lat"
  | "lon"
  | "radio_km"
  | "tipos"
  | "meses"
  | "estrella"
  | "conteo_estrella"
> & { foto: string | null };

function normal(t: string) {
  return t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

export default function ExploradorSafaris({
  parques,
  especies,
  recientes,
  mesHoy,
}: {
  parques: ParqueBreve[];
  especies: { taxon: number; nombre: string }[];
  recientes: Recientes | null;
  mesHoy: number;
}) {
  const [parametros, actualizar] = useParametrosUrl();
  const texto = parametros.get("q") ?? "";
  const continente = parametros.get("continente") ?? "";
  const tipo = parametros.get("tipo") ?? "";
  const especie = parametros.get("especie") ?? "";
  const mes = parametros.has("mes") ? Number(parametros.get("mes")) : mesHoy;
  const tipos = useMemo(() => [...new Set(parques.flatMap((p) => p.tipos))].sort(), [parques]);

  const lista = useMemo(() => {
    const q = normal(texto.trim());
    return parques
      .filter(
        (p) =>
          (!continente || p.continente === continente) &&
          (!tipo || p.tipos.includes(tipo)) &&
          (!especie || (p.conteo_estrella?.[especie] ?? 0) > 0 || p.estrella.includes(Number(especie))) &&
          (!q || normal(`${p.nombre} ${p.pais}`).includes(q)),
      )
      .map((p) => ({ p, puntos: puntuacionAhora(p as Parque, mes, mes === mesHoy ? recientes : null) }))
      .sort((a, b) => b.puntos - a.puntos)
      .map((x) => x.p);
  }, [parques, texto, continente, tipo, especie, mes, mesHoy, recientes]);

  const puntos = useMemo(
    () =>
      lista.map((p) => ({
        id: p.id,
        nombre: `${p.nombre} (${p.pais})`,
        lat: p.lat,
        lon: p.lon,
        radio_km: p.radio_km,
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
            onChange={(e) => actualizar({ q: e.target.value })}
            placeholder="Parque o país: Serengeti, Botsuana, India…"
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
              {CONTINENTES.filter((c) => parques.some((p) => p.continente === c)).map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <label className="campo">
            <span className="rotulo">Qué quieres ver</span>
            <select value={especie} onChange={(e) => actualizar({ especie: e.target.value })}>
              <option value="">Cualquier especie</option>
              {especies.map((e) => (
                <option key={e.taxon} value={e.taxon}>
                  {e.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="campo">
            <span className="rotulo">Tipo de safari</span>
            <select value={tipo} onChange={(e) => actualizar({ tipo: e.target.value })}>
              <option value="">Cualquiera</option>
              {tipos.map((t) => (
                <option key={t} value={t}>
                  {TEXTO_TIPO[t] ?? t}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="fauna-grid">
        <section className="seccion">
          <h2 className="rotulo" aria-live="polite">
            {lista.length} parques · primero los que están en temporada en {MESES[mes]}
          </h2>
          <ul className="rejilla-especies rejilla-safaris">
            {lista.map((p) => (
              <li key={p.id} className="tarjeta-especie">
                {p.foto ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={p.foto} alt="" loading="lazy" decoding="async" />
                ) : (
                  <span className="sin-foto" aria-hidden />
                )}
                <div>
                  <h3>
                    <Link href={`/safaris/${p.id}`}>{p.nombre}</Link>
                  </h3>
                  <p className="meta">
                    {p.pais} · {p.tipos.map((t) => TEXTO_TIPO[t] ?? t).join(", ")}
                  </p>
                  <p className={enTemporada(p, mes) ? "en-temporada" : "fuera-temporada"}>
                    {enTemporada(p, mes) ? `Buena época en ${MESES[mes]}` : `Mejor en otra época`}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </section>
        <div className="seccion mapa-mes">
          <MapaEventos eventos={puntos} enlace="/safaris" etiqueta="Mapa de parques de safari" mundo />
        </div>
      </div>
    </div>
  );
}
