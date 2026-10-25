// Observaciones por mes: doce barras relativas al mes con más (la época con más vida y más observadores). Con
// `relativo`, los valores ya son un índice de 0 a 100 (lo fácil que es verla ese mes).
import { INICIALES, MESES } from "@/features/eventos/modelo";

export default function MesesFauna({
  meses,
  mesActual,
  relativo = false,
}: {
  meses: number[];
  mesActual?: number;
  relativo?: boolean;
}) {
  const max = Math.max(1, ...meses);
  return (
    <div
      className="meses-fauna"
      role="img"
      aria-label={relativo ? "Facilidad de verla cada mes" : "Observaciones por mes"}
    >
      {meses.map((v, i) => (
        <div
          key={i}
          className={i === mesActual ? "actual" : undefined}
          title={relativo ? `${MESES[i]}: ${v} sobre 100` : `${MESES[i]}: ${v} observaciones`}
        >
          <span style={{ height: `${Math.max(4, (v / max) * 100)}%` }} />
          <small>{INICIALES[i]}</small>
        </div>
      ))}
    </div>
  );
}
