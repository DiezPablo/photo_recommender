import Link from "next/link";
import BarraAnual from "@/features/eventos/componentes/BarraAnual";
import { type Categoria, type EventoNaturaleza, fechaCorta, mesDe } from "@/features/eventos/modelo";

export default function TarjetaEvento({
  evento: e,
  categorias,
  mes,
  km,
}: {
  evento: EventoNaturaleza;
  categorias: Record<Categoria, string>;
  /** mes que se está mirando (0-11): resalta si es su mejor momento */
  mes?: number;
  /** distancia desde el spot o la ruta que se está viendo */
  km?: number;
}) {
  const enPico = mes !== undefined && mesDe(e.pico) === mes;
  return (
    <article className={`tarjeta-evento cat-${e.categoria}`}>
      <p className="rotulo">
        <span className="punto-cat" aria-hidden /> {categorias[e.categoria]}
        {enPico && <span className="en-pico">En su mejor momento</span>}
      </p>
      <h3>
        <Link href={`/evento/${e.id}`}>{e.nombre}</Link>
      </h3>
      <p className="meta">
        <span>
          {fechaCorta(e.desde)} – {fechaCorta(e.hasta)}
        </span>
        <span>{km !== undefined ? (km < 1 ? "aquí" : `a ${Math.round(km)} km`) : (e.provincia ?? e.lugar)}</span>
      </p>
      <BarraAnual evento={e} mesActual={mes} compacta />
      <p className="descripcion">{e.descripcion}</p>
    </article>
  );
}
