// Los doce meses con los que ocupa el evento y una marca en su mejor momento. Sin JavaScript.
import { activoEnMes, type EventoNaturaleza, fechaCorta, INICIALES, mesDe } from "@/features/eventos/modelo";

export default function BarraAnual({
  evento,
  mesActual,
  compacta = false,
}: {
  evento: Pick<EventoNaturaleza, "desde" | "hasta" | "pico" | "categoria">;
  mesActual?: number;
  compacta?: boolean;
}) {
  const pico = mesDe(evento.pico);
  return (
    <div
      className={`barra-anual cat-${evento.categoria}${compacta ? " compacta" : ""}`}
      role="img"
      aria-label={`Del ${fechaCorta(evento.desde)} al ${fechaCorta(evento.hasta)}; mejor hacia el ${fechaCorta(evento.pico)}`}
    >
      {INICIALES.map((l, i) => (
        <span
          key={i}
          className={[activoEnMes(evento, i) && "activo", i === pico && "pico", i === mesActual && "actual"]
            .filter(Boolean)
            .join(" ")}
        >
          {!compacta && l}
        </span>
      ))}
    </div>
  );
}
