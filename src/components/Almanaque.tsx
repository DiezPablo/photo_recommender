// Tabla de los próximos días: cada fila es un tipo de salida y cada columna un día, con cuántos spots
// tienen nota excelente (≥ 8) esa jornada; a escala nacional la mejor nota casi siempre es un 10 y no dice
// nada. Es también el filtro de la portada (todo son enlaces, sin JavaScript).
import Link from "next/link";
import { etiquetaDia, type Filtro, FILTROS, NOMBRE_CORTO } from "@/lib/modelo";

export type Mejor = { nota: number; nombre: string; excelentes: number } | null;

/** Tinte de la casilla según cuántos spots excelentes hay, relativo al máximo de la tabla. */
function nivel(n: number, max: number): string {
  if (n === 0) return "n-floja";
  const r = n / Math.max(max, 1);
  return r > 0.6 ? "n-top" : r > 0.25 ? "n-buena" : "n-regular";
}

export default function Almanaque({ fechas, mejores, d, filtro, ruta }: {
  fechas: string[];
  /** mejores[filtro][día] */
  mejores: Record<string, Mejor[]>;
  d: number;
  filtro: Filtro;
  ruta: (d: number, f: Filtro) => string;
}) {
  const max = Math.max(...Object.values(mejores).flat().map((x) => x?.excelentes ?? 0));
  return (
    <nav className="filtros almanaque" aria-label="Día y tipo de salida"
      style={{ gridTemplateColumns: `minmax(5.5rem, auto) repeat(${fechas.length}, minmax(0, 1fr))` }}>
      <span className="alm-esquina">Spots ≥ 8</span>
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
              <Link key={f} href={ruta(i, m)} className={`alm-celda ${nivel(b.excelentes, max)}${actual ? " actual" : ""}`}
                title={`${NOMBRE_CORTO[m]}, ${etiquetaDia(f, i).largo}: ${b.excelentes} spots con 8 o más; el mejor, ${b.nombre} (${b.nota.toFixed(1)})`}
                aria-label={`${NOMBRE_CORTO[m]}, ${etiquetaDia(f, i).largo}: ${b.excelentes} spots excelentes`}>
                {b.excelentes > 0 ? b.excelentes : <span className="alm-mejor">{b.nota.toFixed(1)}</span>}
              </Link>
            ) : <span key={f} className="alm-celda vacia">·</span>;
          })}
        </div>
      ))}
    </nav>
  );
}
