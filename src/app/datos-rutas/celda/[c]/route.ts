// Trazados simplificados de las rutas que empiezan en una celda de 1°: el mapa general solo descarga
// las celdas que tiene a la vista cuando se acerca.
import { cargarRutas, celda } from "@/features/rutas/datos";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  const celdas = new Set(cargarRutas().rutas.map((r) => celda(r.inicio[0], r.inicio[1])));
  return celdas.size ? [...celdas].map((c) => ({ c })) : [{ c: "0_0" }];
}

export async function GET(_: Request, { params }: { params: Promise<{ c: string }> }) {
  const { c } = await params;
  return Response.json(
    cargarRutas()
      .rutas.filter((r) => celda(r.inicio[0], r.inicio[1]) === c)
      .map((r) => ({ id: r.id, nombre: r.nombre, tipo: r.tipo, l: r.linea_mapa })),
  );
}
