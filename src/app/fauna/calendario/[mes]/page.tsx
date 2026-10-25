import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PestanasCalendario } from "@/features/eventos/componentes/NavMeses";
import VistaMesFauna from "@/features/fauna/componentes/VistaMesFauna";
import { cargarEventos, MESES } from "@/features/eventos/datos";

type Props = { params: Promise<{ mes: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return MESES.map((mes) => ({ mes }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { mes } = await params;
  return { title: `Fauna en ${mes}`, description: `Qué fauna se puede ver en ${mes} en España y dónde.` };
}

export default async function PaginaMesFauna({ params }: Props) {
  const mes = MESES.indexOf((await params).mes);
  if (mes < 0) notFound();
  const eventos = cargarEventos();
  const mesHoy = Number((eventos?.desde ?? new Date().toISOString()).slice(5, 7)) - 1;
  return (
    <main className="calendario">
      <header className="titular">
        <p className="rotulo">Calendario de fauna</p>
        <h1>Qué fauna ver en {MESES[mes]}</h1>
        <PestanasCalendario ambito="fauna" mes={mes} />
      </header>
      {eventos ? (
        <VistaMesFauna eventos={eventos} mes={mes} mesHoy={mesHoy} />
      ) : (
        <p>El calendario aún no está disponible.</p>
      )}
    </main>
  );
}
