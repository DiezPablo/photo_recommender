// En la ficha de un spot o de una ruta: qué se puede ver alrededor en cada época del año.
import Link from "next/link";
import TarjetaEvento from "@/features/eventos/componentes/TarjetaEvento";
import { cargarEventos, eventosCerca } from "@/features/eventos/datos";

export default function EventosCerca({ lat, lon, max = 6 }: { lat: number; lon: number; max?: number }) {
  const eventos = cargarEventos();
  if (!eventos) return null;
  const cerca = eventosCerca(lat, lon).slice(0, max);
  if (!cerca.length) return null;
  return (
    <section className="seccion eventos-cerca">
      <h2 className="rotulo">A lo largo del año</h2>
      <div className="rejilla-eventos">
        {cerca.map((e) => (
          <TarjetaEvento key={e.id} evento={e} categorias={eventos.categorias} km={e.km} />
        ))}
      </div>
      <p className="nota-pie">
        Fechas habituales: cambian cada año con el tiempo. <Link href="/calendario">Calendario completo</Link>
      </p>
    </section>
  );
}
