// En el calendario de un mes: las alineaciones más vistosas (lunas llenas primero, luego el sol más bajo).
import Link from "next/link";
import { anoDelMes, cargarAlineaciones, type Eventos, fechaCorta, MESES, rumbo } from "@/features/eventos/datos";
import { cargar } from "@/features/spots/datos";

export default function AlineacionesMes({ eventos, mes, max = 10 }: { eventos: Eventos; mes: number; max?: number }) {
  const datos = cargarAlineaciones();
  if (!datos) return null;
  const prefijo = `${anoDelMes(eventos, mes)}-${String(mes + 1).padStart(2, "0")}`;
  const spots = new Map(cargar().spots.map((s) => [s.id, s]));
  const lista = Object.entries(datos.spots)
    .flatMap(([id, as]) => as.filter((a) => a.fecha.startsWith(prefijo)).map((a) => ({ ...a, spot: spots.get(id) })))
    .filter((a) => a.spot)
    .sort(
      (a, b) =>
        Number(b.cuerpo === "luna") - Number(a.cuerpo === "luna") ||
        a.altura - b.altura ||
        a.fecha.localeCompare(b.fecha),
    );
  if (!lista.length) return null;
  return (
    <section className="seccion alineaciones-mes" aria-labelledby="alineaciones-mes">
      <h2 className="rotulo" id="alineaciones-mes">
        Sol y luna por los picos · {MESES[mes]} · {lista.length} en total
      </h2>
      <ul className="lista-cercanos">
        {lista.slice(0, max).map((a) => (
          <li key={`${a.spot!.id}-${a.cuerpo}-${a.fecha}-${a.azimut}`} className={`alineacion-${a.cuerpo}`}>
            <Link href={`/spot/${a.spot!.id}`}>{a.spot!.nombre}</Link>
            <small>
              {fechaCorta(a.fecha)}, {a.hora} · {a.cuerpo === "sol" ? "el sol" : `la luna llena (${a.iluminacion} %)`}{" "}
              {a.evento} por el pico del {rumbo(a.azimut)}
              {a.spot!.provincia ? ` · ${a.spot!.provincia}` : ""}
            </small>
          </li>
        ))}
      </ul>
    </section>
  );
}
