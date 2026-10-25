import type { Metadata } from "next";
import { notFound } from "next/navigation";
import VistaMes from "@/features/eventos/componentes/VistaMes";
import { cargarEventos, MESES } from "@/features/eventos/datos";

type Props = { params: Promise<{ mes: string }> };

export const dynamicParams = false;

export function generateStaticParams() {
  return MESES.map((mes) => ({ mes }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { mes } = await params;
  return {
    title: `Calendario de ${mes}`,
    description: `Qué fotografiar en ${mes} en España: naturaleza, luna, meteoros y Vía Láctea.`,
  };
}

export default async function PaginaMes({ params }: Props) {
  const mes = MESES.indexOf((await params).mes);
  if (mes < 0) notFound();
  const eventos = cargarEventos();
  const mesHoy = Number((eventos?.desde ?? new Date().toISOString()).slice(5, 7)) - 1;
  return (
    <main className="calendario">
      <header className="titular">
        <p className="rotulo">Calendario</p>
        <h1>Qué fotografiar en {MESES[mes]}</h1>
      </header>
      {eventos ? (
        <VistaMes eventos={eventos} mes={mes} mesHoy={mesHoy} />
      ) : (
        <p>El calendario aún no está disponible.</p>
      )}
    </main>
  );
}
