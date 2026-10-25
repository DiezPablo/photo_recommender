import type { Metadata } from "next";
import { PestanasCalendario } from "@/features/eventos/componentes/NavMeses";
import VistaMesFauna from "@/features/fauna/componentes/VistaMesFauna";
import { cargarEventos, MESES } from "@/features/eventos/datos";

export const metadata: Metadata = {
  title: "Calendario de fauna",
  description: "Qué fauna se puede ver cada mes en España: berrea, grullas, aves migratorias, lince, cetáceos…",
};

export default function PaginaCalendarioFauna() {
  const eventos = cargarEventos();
  const mes = Number((eventos?.desde ?? new Date().toISOString()).slice(5, 7)) - 1;
  return (
    <main className="calendario">
      <header className="titular">
        <p className="rotulo">Calendario de fauna · {MESES[mes]}</p>
        <h1>Qué fauna ver este mes</h1>
        <PestanasCalendario ambito="fauna" />
      </header>
      {eventos ? (
        <VistaMesFauna eventos={eventos} mes={mes} mesHoy={mes} />
      ) : (
        <p>El calendario aún no está disponible.</p>
      )}
    </main>
  );
}
