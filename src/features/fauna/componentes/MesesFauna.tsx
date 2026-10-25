// Observaciones por mes: doce barras relativas al mes con más (la época con más vida y más observadores).
import { INICIALES, MESES } from "@/features/eventos/modelo";

export default function MesesFauna({ meses, mesActual }: { meses: number[]; mesActual?: number }) {
  const max = Math.max(1, ...meses);
  return (
    <div className="meses-fauna" role="img" aria-label="Observaciones por mes">
      {meses.map((v, i) => (
        <div key={i} className={i === mesActual ? "actual" : undefined} title={`${MESES[i]}: ${v} observaciones`}>
          <span style={{ height: `${Math.max(4, (v / max) * 100)}%` }} />
          <small>{INICIALES[i]}</small>
        </div>
      ))}
    </div>
  );
}
