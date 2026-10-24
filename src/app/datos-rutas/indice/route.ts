// Todas las rutas en forma compacta (lista, filtros y puntos del mapa). Estático, generado en el build.
import { cargarRutas, filaRuta } from "@/features/rutas/datos";

export const dynamic = "force-static";

export function GET() {
  return Response.json(cargarRutas().rutas.map(filaRuta));
}
