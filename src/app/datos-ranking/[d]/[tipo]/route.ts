// JSON estático con todos los spots de un día y tipo (compacto): lo usan el mapa y los filtros de
// distancia y comunidad. Se genera en el build, como las páginas.
import { cargar, FILTROS, type Filtro } from "@/lib/datos";
import { filasRanking } from "@/lib/ranking";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  const n = Math.max(cargar().informe?.fechas.length ?? 0, 1);
  return Array.from({ length: n }, (_, d) => FILTROS.map((tipo) => ({ d: String(d), tipo }))).flat();
}

export async function GET(_: Request, { params }: { params: Promise<{ d: string; tipo: string }> }) {
  const { d, tipo } = await params;
  // sin los motivos largos: el JSON lo descarga el móvil
  const filas = filasRanking(Number(d), tipo as Filtro).map((f) => ({ ...f, motivos: f.motivos.slice(0, 1) }));
  return Response.json(filas);
}
