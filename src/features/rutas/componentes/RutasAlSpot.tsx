// En la ficha de un spot: rutas cuyo punto más alto es el spot, con la hora de salida para el amanecer y el
// atardecer de hoy y mañana.
import Link from "next/link";
import MarcaSendero from "@/features/rutas/componentes/MarcaSendero";
import { duracion, rutasQueSuben } from "@/features/rutas/datos";
import { planDia } from "@/features/rutas/planLuz";
import { fechaLocal, horaLocal } from "@/lib/sol";

function diaCorto(fecha: string) {
  return new Date(`${fecha}T12:00:00Z`).toLocaleDateString("es-ES", {
    weekday: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

export default function RutasAlSpot({ lat, lon, max = 4 }: { lat: number; lon: number; max?: number }) {
  const rutas = rutasQueSuben(lat, lon).slice(0, max);
  if (!rutas.length) return null;
  const ahora = new Date();
  const fechas = [0, 1].map((d) => fechaLocal(ahora, d, lon));
  return (
    <section className="seccion rutas-al-spot">
      <h2 className="rotulo">Subir andando</h2>
      <ul className="lista-cercanos">
        {rutas.map(({ ruta: r, cima }) => (
          <li key={r.id}>
            <MarcaSendero tipo={r.tipo} /> <Link href={`/ruta/${r.id}`}>{r.nombre}</Link>
            <small>
              {cima.km.toLocaleString("es-ES")} km y {duracion(cima.horasSubida)} hasta aquí · {r.dificultad}
            </small>
            {fechas.map((f) => {
              const p = planDia(f, cima.lat, cima.lon, cima.horasSubida, cima.horasBajada);
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
