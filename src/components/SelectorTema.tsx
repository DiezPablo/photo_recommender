"use client";
// Claro / oscuro / noche (rojo). Sin elección guardada se sigue al sistema (claro u oscuro).
import { useEffect, useState } from "react";

type Tema = "claro" | "oscuro" | "noche";
const TEMAS: { id: Tema; titulo: string; corto: string }[] = [
  { id: "claro", titulo: "Tema claro", corto: "Día" },
  { id: "oscuro", titulo: "Tema oscuro", corto: "Noche" },
  { id: "noche", titulo: "Modo noche (rojo, para el campo)", corto: "Rojo" },
];

function temaActual(): Tema {
  const t = document.documentElement.dataset.tema as Tema | undefined;
  if (t) return t;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "oscuro" : "claro";
}

// El cambio de tema lo hace el script en línea de layout.tsx (funciona antes de que cargue React);
// aquí solo se refleja qué botón está activo.
export default function SelectorTema() {
  const [tema, setTema] = useState<Tema | null>(null);
  useEffect(() => {
    setTema(temaActual());
    const f = (e: Event) => setTema((e as CustomEvent<Tema>).detail);
    window.addEventListener("tema", f);
    return () => window.removeEventListener("tema", f);
  }, []);

  return (
    <div className="temas" role="group" aria-label="Tema de color">
      {TEMAS.map(({ id, titulo, corto }) => (
        <button key={id} type="button" title={titulo} aria-label={titulo} aria-pressed={tema === id}
          data-tema-boton={id}>
          {corto}
        </button>
      ))}
    </div>
  );
}
