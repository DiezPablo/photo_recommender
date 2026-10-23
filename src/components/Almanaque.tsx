// Tabla de los próximos días: cada fila es un tipo de salida y cada columna un día, con la mejor nota
// de España en esa casilla. Es también el filtro de la portada (todo son enlaces, sin JavaScript).
import Link from "next/link";
import { calificacion, etiquetaDia, type Filtro, FILTROS, NOMBRE_CORTO } from "@/lib/modelo";

export type Mejor = { nota: number; nombre: string } | null;

export default function Almanaque({ fechas, mejores, d, filtro, ruta }: {
  fechas: string[];
  /** mejores[filtro][día] */
  mejores: Record<string, Mejor[]>;
  d: number;
  filtro: Filtro;
  ruta: (d: number, f: Filtro) => string;
}) {
  return (
    <nav className="filtros almanaque" aria-label="Día y tipo de salida"
      style={{ gridTemplateColumns: `minmax(5.5rem, auto) repeat(${fechas.length}, minmax(0, 1fr))` }}>
      <span className="alm-esquina">Mejor nota</span>
      {fechas.map((f, i) => {
        const e = etiquetaDia(f, i);
        return (
          <Link key={f} href={ruta(i, filtro)} className="alm-dia" aria-current={i === d ? "page" : undefined}>
            {i < 2 ? e.corto : e.corto.charAt(0).toUpperCase() + e.corto.slice(1)}
            <small>{e.largo.split(" ")[1]}</small>
          </Link>
        );
      })}
      {FILTROS.map((m) => (
        <div key={m} className={`alm-fila${m === filtro ? " activa" : ""}`} role="presentation">
          <Link href={ruta(d, m)} className="alm-tipo" aria-current={m === filtro ? "page" : undefined}>
            {NOMBRE_CORTO[m]}
          </Link>
          {fechas.map((f, i) => {
            const b = mejores[m]?.[i];
            const actual = i === d && m === filtro;
            return b ? (
              <Link key={f} href={ruta(i, m)} className={`alm-celda ${calificacion(b.nota).clase}${actual ? " actual" : ""}`}
                title={`${NOMBRE_CORTO[m]}, ${etiquetaDia(f, i).largo}: ${b.nota.toFixed(1)} en ${b.nombre}`}
                aria-label={`${NOMBRE_CORTO[m]}, ${etiquetaDia(f, i).largo}: hasta ${b.nota.toFixed(1)}`}>
                {b.nota.toFixed(1)}
              </Link>
            ) : <span key={f} className="alm-celda vacia">·</span>;
          })}
        </div>
      ))}
    </nav>
  );
}
