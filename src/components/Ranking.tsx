"use client";
// Ranking del día. Llega renderizado desde el servidor (funciona sin JavaScript); con JavaScript
// añade la distancia a tu ubicación, el filtro por distancia y el orden por cercanía.
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { NOMBRE_CORTO } from "@/lib/modelo";
import { distanciaKm, guardarUbicacion, leerUbicacion, type Ubicacion } from "@/lib/ubicacion";
import { IconoCamara, IconoFlecha, IconoMomento, IconoUbicacion } from "./Iconos";
import type { FilaRanking } from "./tipos";

const RADIOS = [0, 25, 50, 100, 200];

export default function Ranking({ filas, mostrarMomento }: { filas: FilaRanking[]; mostrarMomento: boolean }) {
  const [ubic, setUbic] = useState<Ubicacion | null>(null);
  const [radio, setRadio] = useState(0);
  const [orden, setOrden] = useState<"nota" | "distancia">("nota");
  const [estado, setEstado] = useState<string>("");
  const [js, setJs] = useState(false);

  useEffect(() => {
    setJs(true);
    setUbic(leerUbicacion());
    try {
      setRadio(Number(localStorage.getItem("radio") ?? 0) || 0);
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

  const visibles = useMemo(() => {
    const conDist = filas.map((f) => ({ ...f, km: ubic ? distanciaKm(ubic, f) : null }));
    const filtradas = conDist.filter((f) => !radio || f.km === null || f.km <= radio);
    if (orden === "distancia" && ubic) filtradas.sort((a, b) => (a.km ?? 0) - (b.km ?? 0));
    return filtradas;
  }, [filas, ubic, radio, orden]);

  return (
    <>
      {js && (
        <div className="herramientas">
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
              <IconoUbicacion size={16} /> Cerca de mí
            </button>
          )}
          {estado && <span role="status">{estado}</span>}
        </div>
      )}
      {visibles.length === 0 ? (
        <p className="vacio">Ningún spot a menos de {radio} km. Amplía la distancia.</p>
      ) : (
        <ol className="ranking" aria-label="Ranking de spots">
          {visibles.map((f) => (
            <li key={f.id}>
              <Link href={`/spot/${f.id}`} className="fila" data-spot={f.id}>
                <span className={`nota ${f.clase}`} aria-label={`Nota ${f.nota} sobre 10`}>
                  {f.nota.toFixed(1)}
                </span>
                <div className="fila-txt">
                  <h3>{f.nombre}</h3>
                  <div className="meta">
                    {mostrarMomento && (
                      <span style={{ display: "inline-flex", gap: 4, alignItems: "center" }}>
                        <IconoMomento momento={f.momento} size={14} /> {NOMBRE_CORTO[f.momento]}
                      </span>
                    )}
                    <span>{f.hora}</span>
                    {f.tipo && <span>{f.tipo}</span>}
                    {f.autores > 0 && <span title="Fotógrafos distintos con fotos aquí en Wikimedia Commons" style={{ display: "inline-flex", gap: 3, alignItems: "center" }}><IconoCamara size={13} /> {f.autores}</span>}
                    {f.km !== null && <span className="dist">{f.km < 10 ? f.km.toFixed(1) : Math.round(f.km)} km</span>}
                  </div>
                  {f.motivos.length > 0 && <p className="por-que">{f.motivos.join(" · ")}</p>}
                </div>
                <span className="flecha"><IconoFlecha /></span>
              </Link>
            </li>
          ))}
        </ol>
      )}
    </>
  );
}
