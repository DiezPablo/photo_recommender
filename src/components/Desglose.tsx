import { calificacion, type Momento, NOMBRE_MOMENTO, type NotaMomento, TEXTO_CONFIANZA } from "@/lib/modelo";
import { IconoMomento } from "./Iconos";

/** Tarjeta de una nota con su desglose: qué suma y qué resta. */
export default function Desglose({ momento, n, subtitulo }: { momento: Momento; n: NotaMomento; subtitulo: string }) {
  const cal = calificacion(n.nota);
  const max = Math.max(...n.desglose.slice(1).map((f) => Math.abs(f.puntos)), 1);
  const suma = n.desglose.reduce((a, f) => a + f.puntos, 0);
  return (
    <article className="nota-tarjeta" data-momento={momento}>
      <header>
        <span className={`nota grande ${cal.clase}`}>
          {n.nota.toFixed(1)}
          <small>{cal.texto}</small>
        </span>
        <div>
          <h3 style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <IconoMomento momento={momento} /> {NOMBRE_MOMENTO[momento]}
          </h3>
          <p>{subtitulo}</p>
          {n.confianza && (
            <p className={`confianza c-${n.confianza}`} title="Misma nota calculada con las nubes de un segundo modelo (ECMWF)">
              {TEXTO_CONFIANZA[n.confianza]}
            </p>
          )}
        </div>
      </header>
      <ul className="desglose" aria-label={`Desglose de la nota de ${NOMBRE_MOMENTO[momento]}`}>
        {n.desglose.map((f, i) => {
          const clase = i === 0 ? "base" : f.puntos > 0 ? "mas" : f.puntos < 0 ? "menos" : "base";
          return (
            <li key={i} className={clase}>
              <span>{f.texto}</span>
              <span className="pts">{i === 0 ? f.puntos.toFixed(1) : `${f.puntos > 0 ? "+" : f.puntos < 0 ? "−" : "±"}${Math.abs(f.puntos).toFixed(1)}`}</span>
              {i > 0 && f.puntos !== 0 && (
                <span className="barra" aria-hidden="true"><i style={{ width: `${(Math.abs(f.puntos) / max) * 100}%` }} /></span>
              )}
            </li>
          );
        })}
        <li className="total">
          <span>Nota{suma > 10 || suma < 0 ? " (se recorta a 0-10)" : ""}</span>
          <span className="pts">{n.nota.toFixed(1)}</span>
        </li>
      </ul>
    </article>
  );
}
