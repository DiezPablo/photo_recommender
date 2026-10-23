// Nota 0-10 como anillo de progreso (SVG, sin JavaScript).
import { calificacion } from "@/lib/modelo";

export default function Anillo({ nota, tam = 56, grosor = 5, etiqueta = true }: {
  nota: number;
  tam?: number;
  grosor?: number;
  etiqueta?: boolean;
}) {
  const cal = calificacion(nota);
  const r = (tam - grosor) / 2;
  const c = 2 * Math.PI * r;
  return (
    <span className={`anillo ${cal.clase}`} style={{ width: tam, height: tam }} role="img"
      aria-label={`Nota ${nota.toFixed(1)} sobre 10: ${cal.texto}`}>
      <svg width={tam} height={tam} viewBox={`0 0 ${tam} ${tam}`} aria-hidden="true">
        <circle cx={tam / 2} cy={tam / 2} r={r} fill="none" stroke="var(--pista)" strokeWidth={grosor} />
        <circle cx={tam / 2} cy={tam / 2} r={r} fill="none" stroke="var(--color-nota)" strokeWidth={grosor}
          strokeLinecap="round" strokeDasharray={`${(c * Math.max(0, Math.min(10, nota))) / 10} ${c}`}
          transform={`rotate(-90 ${tam / 2} ${tam / 2})`} />
      </svg>
      <span className="anillo-num" style={{ fontSize: tam * 0.34 }}>{nota.toFixed(1)}</span>
      {etiqueta && tam >= 64 && <span className="anillo-txt">{cal.texto}</span>}
    </span>
  );
}
