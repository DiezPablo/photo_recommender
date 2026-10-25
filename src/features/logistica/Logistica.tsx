// «Para ir»: aparcamientos, fuentes, refugios, áreas de autocaravanas y campings cerca (OpenStreetMap).
import { cargarLogistica, type PuntoLogistica, type TipoLogistica } from "@/features/logistica/datos";

const ORDEN: TipoLogistica[] = ["aparcamiento", "fuente", "refugio", "autocaravanas", "camping"];
const NOMBRE: Record<TipoLogistica, string> = {
  aparcamiento: "Aparcamiento",
  fuente: "Agua",
  refugio: "Refugio",
  autocaravanas: "Autocaravanas",
  camping: "Camping",
};

function distancia(km: number) {
  return km < 1
    ? `a ${Math.round((km * 1000) / 10) * 10} m`
    : `a ${km.toLocaleString("es-ES", { maximumFractionDigits: 1 })} km`;
}

export default function Logistica({ tipo, id }: { tipo: "spots" | "rutas"; id: string }) {
  const lista = cargarLogistica()?.[tipo][id];
  if (!lista?.length) return null;
  const grupos = ORDEN.map((t) => ({ t, ps: lista.filter((p) => p.tipo === t) })).filter((g) => g.ps.length);
  return (
    <section className="seccion logistica">
      <h2 className="rotulo">Para ir</h2>
      <dl className="lista-logistica">
        {grupos.map(({ t, ps }) => (
          <div key={t}>
            <dt>{NOMBRE[t]}</dt>
            {ps.map((p: PuntoLogistica) => (
              <dd key={p.osm}>
                <a href={`https://www.openstreetmap.org/${p.osm}`} rel="noopener">
                  {p.nombre ?? (p.detalle ? p.detalle[0].toUpperCase() + p.detalle.slice(1) : NOMBRE[t])}
                </a>
                {p.nombre && p.detalle && ` (${p.detalle})`} · {distancia(p.km)}
                {t === "aparcamiento" && (
                  <>
                    {" · "}
                    <a
                      href={`https://www.google.com/maps/dir/?api=1&destination=${p.lat},${p.lon}`}
                      target="_blank"
                      rel="noopener"
                    >
                      cómo llegar ↗
                    </a>
                  </>
                )}
              </dd>
            ))}
          </div>
        ))}
      </dl>
      <p className="nota-pie">
        En línea recta, según OpenStreetMap: comprueba accesos, horarios y que el agua sea potable antes de ir.
      </p>
    </section>
  );
}
