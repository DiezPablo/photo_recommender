"use client";
// Ranking del día. El top nacional llega renderizado desde el servidor (funciona sin JavaScript); con
// JavaScript se descarga la lista completa (JSON estático) para filtrar por distancia a tu ubicación
// y por comunidad autónoma y ordenar por cercanía.
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { NOMBRE_CORTO } from "@/lib/modelo";
import { distanciaKm, guardarUbicacion, leerUbicacion, type Ubicacion } from "@/lib/ubicacion";
import Cifra from "./Cifra";
import type { FilaRanking } from "./tipos";

const RADIOS = [0, 25, 50, 100, 200, 400];
const POR_PAGINA = 60;

export default function Ranking({ filas, total, urlTodos, comunidades, mostrarMomento }: {
  filas: FilaRanking[];
  total: number;
  urlTodos: string;
  comunidades: string[];
  mostrarMomento: boolean;
}) {
  const [ubic, setUbic] = useState<Ubicacion | null>(null);
  const [radio, setRadio] = useState(0);
  const [ccaa, setCcaa] = useState("");
  const [todas, setTodas] = useState<FilaRanking[] | null>(null);
  const [limite, setLimite] = useState(POR_PAGINA);
  const [orden, setOrden] = useState<"nota" | "distancia">("nota");
  const [estado, setEstado] = useState<string>("");
  const [js, setJs] = useState(false);

  useEffect(() => {
    setJs(true);
    setUbic(leerUbicacion());
    try {
      setRadio(Number(localStorage.getItem("radio") ?? 0) || 0);
      setCcaa(localStorage.getItem("ccaa") ?? "");
    } catch {}
    const f = (e: Event) => setUbic((e as CustomEvent<Ubicacion | null>).detail);
    window.addEventListener("ubicacion", f);
    return () => window.removeEventListener("ubicacion", f);
  }, []);

  function pedirUbicacion() {
    if (!navigator.geolocation) return setEstado("Tu navegador no da la ubicación");
    setEstado("Buscando tu ubicación…");
    navigator.geolocation.getCurrentPosition(
      (p) => {
        const u = { lat: +p.coords.latitude.toFixed(3), lon: +p.coords.longitude.toFixed(3) };
        guardarUbicacion(u);
        setUbic(u);
        setEstado("");
      },
      () => setEstado("No se pudo obtener la ubicación"),
      { maximumAge: 600000, timeout: 15000 },
    );
  }

  function cambiarRadio(r: number) {
    setRadio(r);
    try {
      localStorage.setItem("radio", String(r));
    } catch {}
  }

  // La lista completa solo hace falta al filtrar: se pide entonces (es un JSON estático y pequeño)
  const necesitaTodas = !!ubic || !!ccaa || limite > POR_PAGINA;
  useEffect(() => {
    if (!necesitaTodas || todas) return;
    fetch(urlTodos).then((r) => (r.ok ? r.json() : null)).then((d) => d && setTodas(d)).catch(() => {});
  }, [necesitaTodas, todas, urlTodos]);

  function cambiarCcaa(c: string) {
    setCcaa(c);
    setLimite(POR_PAGINA);
    try {
      localStorage.setItem("ccaa", c);
    } catch {}
  }

  const { visibles, coinciden } = useMemo(() => {
    const base = todas ?? filas;
    const conDist = base.map((f) => ({ ...f, km: ubic ? distanciaKm(ubic, f) : null }));
    const filtradas = conDist.filter((f) => (!radio || f.km === null || f.km <= radio) && (!ccaa || f.ccaa === ccaa));
    if (orden === "distancia" && ubic) filtradas.sort((a, b) => (a.km ?? 0) - (b.km ?? 0));
    return { visibles: filtradas.slice(0, limite), coinciden: filtradas.length };
  }, [filas, todas, ubic, radio, ccaa, orden, limite]);

  return (
    <>
      {js && (
        <div className="herramientas">
          {comunidades.length > 1 && (
            <label>
              <span className="sr">Comunidad autónoma</span>
              <select className="boton" value={ccaa} onChange={(e) => cambiarCcaa(e.target.value)}>
                <option value="">Toda España</option>
                {comunidades.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
          )}
          {ubic ? (
            <>
              <label>
                <span className="sr">Distancia máxima</span>
                <select className="boton" value={radio} onChange={(e) => cambiarRadio(Number(e.target.value))}>
                  {RADIOS.map((r) => (
                    <option key={r} value={r}>{r ? `A menos de ${r} km` : "Cualquier distancia"}</option>
                  ))}
                </select>
              </label>
              <label>
                <span className="sr">Ordenar por</span>
                <select className="boton" value={orden} onChange={(e) => setOrden(e.target.value as "nota" | "distancia")}>
                  <option value="nota">Por nota</option>
                  <option value="distancia">Por cercanía</option>
                </select>
              </label>
              <button type="button" className="boton" onClick={() => { guardarUbicacion(null); setUbic(null); }}>
                Olvidar ubicación
              </button>
            </>
          ) : (
            <button type="button" className="boton" onClick={pedirUbicacion}>
              Cerca de mí
            </button>
          )}
          {estado && <span role="status">{estado}</span>}
        </div>
      )}
      {visibles.length === 0 ? (
        <p className="vacio">{todas || !necesitaTodas ? "Ningún spot con esos filtros. Amplía la distancia o cambia de comunidad." : "Cargando…"}</p>
      ) : (
        <ol className="ranking" aria-label="Ranking de spots">
          {visibles.map((f, i) => (
            <li key={f.id}>
              <Link href={`/spot/${f.id}`} className="fila" data-spot={f.id}>
                <span className="pos">{String(i + 1).padStart(2, "0")}</span>
                <Cifra nota={f.nota} />
                <div className="fila-txt">
                  <h3>{f.nombre}</h3>
                  <p className="meta">
                    {mostrarMomento && <span>{NOMBRE_CORTO[f.momento]}</span>}
                    <span>{f.hora}</span>
                    {f.provincia && <span>{f.provincia}</span>}
                    {f.km !== null && <span className="dist">{f.km < 10 ? f.km.toFixed(1) : Math.round(f.km)} km</span>}
                    {f.dudosa && <span className="dudosa" title="Los modelos meteorológicos no coinciden">dudosa</span>}
                  </p>
                  {f.motivos.length > 0 && <p className="por-que">{f.motivos.join(". ")}.</p>}
                </div>
                {f.foto && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img className="fila-foto" src={f.foto} alt="" loading="lazy" width={60} height={60} />
                )}
              </Link>
            </li>
          ))}
        </ol>
      )}
      {js && coinciden > visibles.length && (
        <button type="button" className="boton" onClick={() => setLimite((l) => l + POR_PAGINA)}>
          Ver más ({coinciden - visibles.length} de {todas ? coinciden : total})
        </button>
      )}
    </>
  );
}
