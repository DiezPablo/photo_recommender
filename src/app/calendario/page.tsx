import type { Metadata } from "next";
import VistaMes from "@/features/eventos/componentes/VistaMes";
import { cargarEventos, MESES } from "@/features/eventos/datos";

export const metadata: Metadata = {
  title: "Calendario",
  description:
    "Qué fotografiar en cada época del año en España: floraciones, otoño, berrea, aves, nieve, lunas, lluvias de meteoros, Vía Láctea y eclipses.",
};

/** El mes en curso (la web se reconstruye cada día con los datos nuevos). */
export default function PaginaCalendario() {
  const eventos = cargarEventos();
  const mes = Number((eventos?.desde ?? new Date().toISOString()).slice(5, 7)) - 1;
  return (
    <main className="calendario">
      <header className="titular">
        <p className="rotulo">Calendario · {MESES[mes]}</p>
        <h1>Qué fotografiar este mes</h1>
      </header>
      {eventos ? <VistaMes eventos={eventos} mes={mes} mesHoy={mes} /> : <p>El calendario aún no está disponible.</p>}
    </main>
  );
}
