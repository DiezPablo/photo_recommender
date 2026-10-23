// Matriz tipo de salida × día con la mejor nota de cada casilla: de un vistazo, qué día merece la pena.
import Link from "next/link";
import { etiquetaDia, type Filtro, MOMENTOS, NOMBRE_CORTO, calificacion } from "@/lib/modelo";
import { IconoMomento } from "./Iconos";

export type Mejor = { nota: number; nombre: string } | null;

export default function Semana({ fechas, mejores, d, filtro, ruta }: {
  fechas: string[];
  /** mejores[momento][día] */
  mejores: Record<string, Mejor[]>;
  d: number;
  filtro: Filtro;
  ruta: (d: number, f: Filtro) => string;
}) {
  return (
    <section className="semana tarjeta" aria-label="Mejor nota por día y tipo de salida">
      <h2>Los próximos días</h2>
      <div className="semana-tabla" style={{ gridTemplateColumns: `minmax(84px, auto) repeat(${fechas.length}, 1fr)` }}>
        <span />
        {fechas.map((f, i) => {
          const e = etiquetaDia(f, i);
          return (
            <Link key={f} href={ruta(i, filtro)} className="semana-dia" aria-current={i === d ? "page" : undefined}>
              {e.corto}<small>{e.largo.split(" ")[1]}</small>
            </Link>
          );
        })}
        {MOMENTOS.map((m) => (
          <div key={m} className="semana-fila" style={{ display: "contents" }}>
            <Link href={ruta(d, m)} className="semana-tipo" aria-current={m === filtro ? "true" : undefined}>
              <IconoMomento momento={m} size={15} /> {NOMBRE_CORTO[m]}
            </Link>
            {fechas.map((f, i) => {
              const b = mejores[m]?.[i];
              const actual = i === d && (filtro === m || filtro === "todos");
              return b ? (
                <Link key={f} href={ruta(i, m)} className={`semana-celda ${calificacion(b.nota).clase}${actual ? " actual" : ""}`}
                  title={`${NOMBRE_CORTO[m]}, ${etiquetaDia(f, i).largo}: ${b.nota.toFixed(1)} en ${b.nombre}`}>
                  {b.nota.toFixed(1)}
                </Link>
              ) : <span key={f} className="semana-celda vacia">—</span>;
            })}
          </div>
        ))}
      </div>
    </section>
  );
}
