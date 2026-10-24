"use client";
// Claro / oscuro / noche (rojo). Sin elección guardada se sigue al sistema (claro u oscuro).
import { useSyncExternalStore } from "react";
import { IconoClaro, IconoOjoRojo, IconoOscuro } from "@/ui/Iconos";

type Tema = "claro" | "oscuro" | "noche";
const TEMAS: { id: Tema; titulo: string; corto: string; Icono: typeof IconoClaro }[] = [
  { id: "claro", titulo: "Tema claro", corto: "Día", Icono: IconoClaro },
  { id: "oscuro", titulo: "Tema oscuro", corto: "Noche", Icono: IconoOscuro },
  { id: "noche", titulo: "Modo noche (rojo, para el campo)", corto: "Rojo", Icono: IconoOjoRojo },
];

function temaActual(): Tema {
  const t = document.documentElement.dataset.tema as Tema | undefined;
  if (t) return t;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "oscuro" : "claro";
}

// El cambio de tema lo hace el script en línea de layout.tsx (funciona antes de que cargue React);
// aquí solo se refleja qué botón está activo.
function suscribir(aviso: () => void) {
  const sistema = window.matchMedia("(prefers-color-scheme: dark)");
  window.addEventListener("tema", aviso);
  sistema.addEventListener("change", aviso);
  return () => {
    window.removeEventListener("tema", aviso);
    sistema.removeEventListener("change", aviso);
  };
}

export default function SelectorTema() {
  const tema = useSyncExternalStore<Tema | null>(suscribir, temaActual, () => null);

  return (
    <div className="temas" role="group" aria-label="Tema de color">
      {TEMAS.map(({ id, titulo, corto, Icono }) => (
        <button
          key={id}
          type="button"
          title={titulo}
          aria-label={titulo}
          aria-pressed={tema === id}
          data-tema-boton={id}
        >
          <span className="tema-txt">{corto}</span>
          <span className="tema-ico">
            <Icono size={15} />
          </span>
        </button>
      ))}
    </div>
  );
}
