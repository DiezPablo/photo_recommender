// En la ficha de una ruta: a qué hora salir para tener arriba el amanecer o el atardecer, y con qué nota.
import Link from "next/link";
import Cifra from "@/ui/Cifra";
import type { Cima } from "@/features/rutas/cima";
import { duracion } from "@/features/rutas/modelo";
import { type PlanMomento, planDia } from "@/features/rutas/planLuz";
import { horaLocal } from "@/lib/sol";

export interface NotaLuz {
  amanecer?: number;
  atardecer?: number;
}

function diaCorto(fecha: string) {
  return new Date(`${fecha}T12:00:00Z`).toLocaleDateString("es-ES", {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
}

function Momento({
  m,
  tipo,
  lon,
  nota,
}: {
  m: PlanMomento | null;
  tipo: "amanecer" | "atardecer";
  lon: number;
  nota?: number;
}) {
  if (!m) return <td>—</td>;
  return (
    <td>
      <b className="hora-salida">Sal a las {horaLocal(m.salida, lon)}</b>
      <small>
        {tipo === "amanecer" ? "sale el sol" : "se pone"} a las {horaLocal(m.sol, lon)}
        {nota !== undefined && (
          <>
            {" · nota "}
            <Cifra nota={nota} />
          </>
        )}
      </small>
      {m.minutosDeNoche > 0 && (
        <small className="frontal">
          {tipo === "amanecer"
            ? `${m.minutosDeNoche} min de subida sin luz`
            : `${m.minutosDeNoche} min de bajada sin luz`}
          : frontal
        </small>
      )}
    </td>
  );
}

export default function PlanLuz({
  cima,
  fechas,
  notas,
  spot,
}: {
  cima: Cima;
  fechas: string[];
  /** nota prevista del spot más cercano a la cima, por fecha */
  notas?: Record<string, NotaLuz>;
  spot?: { id: string; nombre: string; km: number };
}) {
  return (
    <section className="seccion plan-luz">
      <h2 className="rotulo">Para la foto en lo alto</h2>
      <p>
        El punto más alto ({cima.alt.toLocaleString("es-ES")} m) está a {cima.km.toLocaleString("es-ES")} km de la
        salida: unas <b>{duracion(cima.horasSubida)}</b> de subida y {duracion(cima.horasBajada)} de{" "}
        {cima.vuelta === "misma" ? "vuelta por el mismo camino" : "bajada hasta el final"}.
        {spot && (
          <>
            {" "}
            La nota es la del spot <Link href={`/spot/${spot.id}`}>{spot.nombre}</Link>
            {spot.km >= 0.3 && `, a ${spot.km.toLocaleString("es-ES", { maximumFractionDigits: 1 })} km`}.
          </>
        )}
      </p>
      <div className="tabla-desplaza">
        <table className="tabla-luz">
          <thead>
            <tr>
              <th scope="col">Día</th>
              <th scope="col">Amanecer arriba</th>
              <th scope="col">Atardecer arriba</th>
            </tr>
          </thead>
          <tbody>
            {fechas.map((f) => {
              const p = planDia(f, cima.lat, cima.lon, cima.horasSubida, cima.horasBajada);
              return (
                <tr key={f}>
                  <th scope="row">{diaCorto(f)}</th>
                  <Momento m={p.amanecer} tipo="amanecer" lon={cima.lon} nota={notas?.[f]?.amanecer} />
                  <Momento m={p.atardecer} tipo="atardecer" lon={cima.lon} nota={notas?.[f]?.atardecer} />
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="nota-pie">
        Para estar arriba 30 min antes de que salga el sol o al empezar la hora dorada, con el tiempo MIDE más un 15 %
        para paradas. Sin luz: antes del alba o después del crepúsculo civil.
      </p>
    </section>
  );
}
