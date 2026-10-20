"use client";
// Claro / oscuro / noche (rojo). Sin elección guardada se sigue al sistema (claro u oscuro).
import { useEffect, useState } from "react";
import { IconoClaro, IconoOjoRojo, IconoOscuro } from "./Iconos";

type Tema = "claro" | "oscuro" | "noche";
const TEMAS: { id: Tema; titulo: string; Icono: typeof IconoClaro }[] = [
  { id: "claro", titulo: "Tema claro", Icono: IconoClaro },
  { id: "oscuro", titulo: "Tema oscuro", Icono: IconoOscuro },
  { id: "noche", titulo: "Modo noche (rojo, para el campo)", Icono: IconoOjoRojo },
];

function temaActual(): Tema {
  const t = document.documentElement.dataset.tema as Tema | undefined;
  if (t) return t;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "oscuro" : "claro";
}

export default function SelectorTema() {
  const [tema, setTema] = useState<Tema | null>(null);
  useEffect(() => setTema(temaActual()), []);

  function elegir(t: Tema) {
    document.documentElement.dataset.tema = t;
    try {
      localStorage.setItem("tema", t);
    } catch {}
    setTema(t);
    window.dispatchEvent(new CustomEvent("tema", { detail: t }));
  }

  return (
    <div className="temas" role="group" aria-label="Tema de color">
      {TEMAS.map(({ id, titulo, Icono }) => (
        <button key={id} type="button" title={titulo} aria-label={titulo} aria-pressed={tema === id}
          onClick={() => elegir(id)}>
          <Icono size={16} />
        </button>
      ))}
    </div>
  );
}
