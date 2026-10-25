// Un mes del calendario de fauna: los eventos (berrea, grullas, celo del lince…) y los observatorios con más
// actividad ese mes. Sin JS salvo el mapa.
import Link from "next/link";
import MapaEventos from "@/features/eventos/componentes/MapaEventos";
import NavMeses from "@/features/eventos/componentes/NavMeses";
import TarjetaEvento from "@/features/eventos/componentes/TarjetaEvento";
import { activoEnMes, ambito, type Eventos, MESES, mesDe } from "@/features/eventos/modelo";
import { cargarFauna, nombreEspecie, POCAS_OBSERVACIONES } from "@/features/fauna/datos";

export default function VistaMesFauna({ eventos, mes, mesHoy }: { eventos: Eventos; mes: number; mesHoy: number }) {
  const activos = eventos.naturaleza
    .filter((e) => ambito(e) === "fauna" && activoEnMes(e, mes))
    .sort((a, b) => Number(mesDe(b.pico) === mes) - Number(mesDe(a.pico) === mes) || a.nombre.localeCompare(b.nombre));
  // observatorios: los que ese mes están en su mejor momento (respecto a su propio año), con datos suficientes
  const lugares = (cargarFauna()?.lugares ?? [])
    .filter((l) => l.observaciones >= POCAS_OBSERVACIONES)
    .map((l) => ({ l, actividad: l.meses[mes] / Math.max(1, ...l.meses) }))
    .filter((x) => x.actividad >= 0.75)
    .sort((a, b) => b.l.meses[mes] - a.l.meses[mes])
    .slice(0, 12)
    .map((x) => x.l);
  const enMapa = [
    ...activos.map((e) => ({
      id: e.id,
      nombre: e.nombre,
      lat: e.lat,
      lon: e.lon,
      radio_km: e.radio_km,
      categoria: "fauna",
    })),
  ];
  return (
    <>
      <NavMeses mes={mes} mesHoy={mesHoy} ambito="fauna" />
      <div className="calendario-grid">
        <section className="seccion" aria-labelledby="eventos-fauna">
          <h2 className="rotulo" id="eventos-fauna">
            Eventos de fauna · {MESES[mes]} · {activos.length}
          </h2>
          <div className="rejilla-eventos una-columna">
            {activos.map((e) => (
              <TarjetaEvento key={e.id} evento={e} categorias={eventos.categorias} mes={mes} />
            ))}
          </div>
          {!activos.length && <p>Ningún evento de fauna de la lista este mes.</p>}
        </section>
        <section className="seccion mapa-mes" aria-label={`Mapa de fauna de ${MESES[mes]}`}>
          <MapaEventos eventos={enMapa} etiqueta={`Mapa de fauna de ${MESES[mes]}`} />
        </section>
      </div>
      {lugares.length > 0 && (
        <section className="seccion" aria-labelledby="lugares-mes">
          <h2 className="rotulo" id="lugares-mes">
            Observatorios en su mejor momento en {MESES[mes]}
          </h2>
          <ul className="lista-cercanos">
            {lugares.map((l) => (
              <li key={l.id}>
                <Link href={`/fauna/${l.id}`}>{l.nombre}</Link>
                <small>
                  {l.provincia} · {l.especies.slice(0, 3).map(nombreEspecie).join(", ")}
                </small>
              </li>
            ))}
          </ul>
          <p className="nota-pie">
            Con más observaciones registradas este mes que en casi cualquier otro (GBIF, 2016-2025).
          </p>
        </section>
      )}
      <p className="nota-pie">
        Fechas habituales: cambian cada año. Respeta las distancias, el silencio y las épocas de cría; en espacios
        protegidos, consulta las normas de acceso.
      </p>
    </>
  );
}
