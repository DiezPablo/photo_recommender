// En una ficha (spot, ruta, lugar de fauna): qué se puede ver alrededor en cada época del año, del paisaje o de
// la fauna (son dos calendarios distintos).
import Link from "next/link";
import TarjetaEvento from "@/features/eventos/componentes/TarjetaEvento";
import { type Ambito, cargarEventos, eventosCerca, rutaCalendario } from "@/features/eventos/datos";

const TITULO: Record<Ambito, string> = { paisaje: "A lo largo del año", fauna: "Fauna a lo largo del año" };

export default function EventosCerca({
  lat,
  lon,
  max = 6,
  ambito = "paisaje",
}: {
  lat: number;
  lon: number;
  max?: number;
  ambito?: Ambito;
}) {
  const eventos = cargarEventos();
  if (!eventos) return null;
  const cerca = eventosCerca(lat, lon, 15, ambito).slice(0, max);
  if (!cerca.length) return null;
  return (
    <section className={`seccion eventos-cerca eventos-${ambito}`}>
      <h2 className="rotulo">{TITULO[ambito]}</h2>
      <div className="rejilla-eventos">
        {cerca.map((e) => (
          <TarjetaEvento key={e.id} evento={e} categorias={eventos.categorias} km={e.km} />
        ))}
      </div>
      <p className="nota-pie">
        Fechas habituales: cambian cada año con el tiempo.{" "}
        <Link href={rutaCalendario(ambito)}>{ambito === "fauna" ? "Calendario de fauna" : "Calendario completo"}</Link>
      </p>
    </section>
  );
}
