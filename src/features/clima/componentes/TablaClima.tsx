// Qué esperar cada mes: una fila por serie y doce celdas teñidas según la frecuencia. Sin JavaScript.
import { INICIALES, MESES } from "@/features/eventos/modelo";
import { NOMBRE_CORTO_SERIE, NOMBRE_SERIE, type PuntoClima, SERIES } from "@/features/clima/modelo";

export default function TablaClima({ punto, mesActual }: { punto: PuntoClima; mesActual?: number }) {
  return (
    <div className="tabla-desplaza">
      <table className="tabla-clima">
        <thead>
          <tr>
            <th scope="col">
              <span className="sr">Serie</span>
            </th>
            {INICIALES.map((l, i) => (
              <th key={i} scope="col" className={i === mesActual ? "actual" : undefined} title={MESES[i]}>
                {l}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {SERIES.map((s) => {
            const max = Math.max(1, ...punto[s].map((v) => v ?? 0));
            return (
              <tr key={s} className={`serie-${s}`}>
                <th scope="row">
                  <span className="largo">{NOMBRE_SERIE[s]}</span>
                  <span className="corto" aria-hidden="true">
                    {NOMBRE_CORTO_SERIE[s]}
                  </span>
                </th>
                {punto[s].map((v, i) => (
                  <td
                    key={i}
                    className={i === mesActual ? "actual" : undefined}
                    // intensidad relativa al mejor mes de la fila: se ve de un vistazo cuándo toca
                    style={{ "--f": v === null ? 0 : v / max } as React.CSSProperties}
                    title={v === null ? `${MESES[i]}: sin datos` : `${MESES[i]}: ${v} %`}
                  >
                    {v ?? "–"}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
