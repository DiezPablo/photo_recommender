import type { Metadata } from "next";
import { notFound } from "next/navigation";
import VistaDia from "@/features/spots/componentes/VistaDia";
import { cargar, etiquetaDia, FILTROS, type Filtro, NOMBRE_MOMENTO } from "@/features/spots/datos";

export const dynamicParams = false;

export function generateStaticParams() {
  const n = Math.max(cargar().informe?.fechas.length ?? 0, 1);
  return Array.from({ length: n }, (_, d) => FILTROS.map((tipo) => ({ d: String(d), tipo }))).flat();
}

type Props = { params: Promise<{ d: string; tipo: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { d, tipo } = await params;
  const fecha = cargar().informe?.fechas[Number(d)];
  return { title: `${NOMBRE_MOMENTO[tipo as Filtro] ?? ""} · ${fecha ? etiquetaDia(fecha, Number(d)).largo : ""}` };
}

export default async function Pagina({ params }: Props) {
  const { d, tipo } = await params;
  const n = Number(d);
  if (!FILTROS.includes(tipo as Filtro) || !Number.isInteger(n) || !cargar().informe?.fechas[n]) notFound();
  return <VistaDia d={n} filtro={tipo as Filtro} />;
}
