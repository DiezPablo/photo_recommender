// El año de un parque: temporada recomendada (escrita a mano), mamíferos observados en iNaturalist por mes y
// clima (lluvia y máxima media de ERA5). Una columna por mes.
import { INICIALES, MESES } from "@/features/eventos/modelo";
import type { Parque } from "@/features/safaris/modelo";

export default function AnoSafari({ p, mesActual }: { p: Parque; mesActual: number }) {
  const lluviaMax = Math.max(1, ...(p.clima?.lluvia_mm ?? [1]));
  return (
    <div className="ano-safari" role="table" aria-label="El año en el parque">
      <div role="row" className="fila-ano cabecera-ano">
        <span role="rowheader" />
        {INICIALES.map((m, i) => (
          <span role="columnheader" key={i} className={i === mesActual ? "actual" : undefined} title={MESES[i]}>
            {m}
          </span>
        ))}
      </div>
      <div role="row" className="fila-ano">
        <span role="rowheader">Temporada</span>
        {MESES.map((m, i) => (
          <span
            role="cell"
            key={m}
            className={p.meses.includes(i + 1) ? "temporada-si" : "temporada-no"}
            title={`${m}: ${p.meses.includes(i + 1) ? "buena época" : "fuera de la mejor época"}`}
          />
        ))}
      </div>
      {p.meses_mamiferos && (
        <div role="row" className="fila-ano">
          <span role="rowheader">Mamíferos vistos</span>
          {p.meses_mamiferos.map((v, i) => (
            <span role="cell" key={i} title={`${MESES[i]}: ${v} sobre 100`} className="barra-ano">
              <i style={{ height: `${Math.max(6, v)}%` }} />
            </span>
          ))}
        </div>
      )}
      {p.clima && (
        <>
          <div role="row" className="fila-ano">
            <span role="rowheader">Lluvia</span>
            {p.clima.lluvia_mm.map((v, i) => (
              <span role="cell" key={i} title={`${MESES[i]}: ${v} mm`} className="barra-ano lluvia">
                <i style={{ height: `${Math.max(4, (v / lluviaMax) * 100)}%` }} />
              </span>
            ))}
          </div>
          <div role="row" className="fila-ano numeros">
            <span role="rowheader">Máx. °C</span>
            {p.clima.tmax.map((v, i) => (
              <span role="cell" key={i}>
                {v ?? "–"}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
