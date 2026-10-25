// En la ficha de un spot: rutas que pasan por él (o acaban en él), con cuánto se tarda en llegar y la hora de
// salida para tenerlo con la luz del amanecer y del atardecer de hoy y mañana.
import Link from "next/link";
import MarcaSendero from "@/features/rutas/componentes/MarcaSendero";
import { duracion, rutasQuePasan } from "@/features/rutas/datos";
import { planDia } from "@/features/rutas/planLuz";
import { fechaLocal, horaLocal } from "@/lib/sol";

function diaCorto(fecha: string) {
  return new Date(`${fecha}T12:00:00Z`).toLocaleDateString("es-ES", {
    weekday: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

export default function RutasAlSpot({ lat, lon, max = 5 }: { lat: number; lon: number; max?: number }) {
  // los que salen casi del mismo spot (menos de 10 min) no son «llegar andando»
  const rutas = rutasQuePasan(lat, lon)
    .filter((x) => x.paso.horasIda >= 1 / 6)
    .slice(0, max);
  if (!rutas.length) return null;
  const ahora = new Date();
  const fechas = [0, 1].map((d) => fechaLocal(ahora, d, lon));
  return (
    <section className="seccion rutas-al-spot">
      <h2 className="rotulo">Llegar andando</h2>
      <ul className="lista-cercanos">
        {rutas.map(({ ruta: r, paso }) => (
          <li key={r.id}>
            <MarcaSendero tipo={r.tipo} /> <Link href={`/ruta/${r.id}`}>{r.nombre}</Link>
            <small>
              Pasa por aquí en el km {paso.km.toLocaleString("es-ES")}: {duracion(paso.horasIda)} desde la salida ·{" "}
              {r.dificultad}
            </small>
            {fechas.map((f) => {
              const p = planDia(f, paso.lat, paso.lon, paso.horasIda, paso.horasVuelta);
              return (
                <small key={f} className="salidas">
                  {diaCorto(f)}: amanecer, sal a las {p.amanecer ? horaLocal(p.amanecer.salida, lon) : "—"} · atardecer,
                  sal a las {p.atardecer ? horaLocal(p.atardecer.salida, lon) : "—"}
                </small>
              );
            })}
          </li>
        ))}
      </ul>
      <p className="nota-pie">
        Hora de salida desde el inicio de la ruta para estar aquí con la mejor luz (tiempo MIDE más un 15 %).
      </p>
    </section>
  );
}
