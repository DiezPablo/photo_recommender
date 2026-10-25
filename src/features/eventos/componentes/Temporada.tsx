// En la portada: qué está en su mejor momento estos días, el paisaje por un lado y la fauna por otro, y accesos
// al planificador y a los dos calendarios.
import Link from "next/link";
import {
  activoEn,
  type Ambito,
  ambito,
  cargarEventos,
  type EventoNaturaleza,
  fechaCorta,
  rutaCalendario,
} from "@/features/eventos/datos";

/** Días entre dos fechas MM-DD dentro del año (el más corto, cruzando año si hace falta). */
function diasEntre(a: string, b: string): number {
  const d = (x: string) => Date.UTC(2027, Number(x.slice(0, 2)) - 1, Number(x.slice(3, 5))) / 864e5;
  const n = Math.abs(d(a) - d(b));
  return Math.min(n, 365 - n);
}

/** Los más cerca de su mejor momento, sin más de dos de la misma categoría (que no salga solo otoño). */
function destacados(lista: EventoNaturaleza[], hoy: string, max: number): EventoNaturaleza[] {
  const md = hoy.slice(5);
  const porCategoria = new Map<string, number>();
  return lista
    .filter((e) => activoEn(e, hoy))
    .sort((a, b) => diasEntre(a.pico, md) - diasEntre(b.pico, md))
    .filter((e) => {
      const n = porCategoria.get(e.categoria) ?? 0;
      porCategoria.set(e.categoria, n + 1);
      return n < 2;
    })
    .slice(0, max);
}

const TITULO: Record<Ambito, string> = { paisaje: "Paisaje", fauna: "Fauna" };

export default function Temporada({ hoy, max = 3 }: { hoy: string; max?: number }) {
  const eventos = cargarEventos();
  if (!eventos) return null;
  const grupos = (["paisaje", "fauna"] as Ambito[]).map((a) => ({
    a,
    lista: destacados(
      eventos.naturaleza.filter((e) => ambito(e) === a),
      hoy,
      max,
    ),
  }));
  return (
    <section className="temporada-portada" aria-labelledby="temporada">
      <h2 className="rotulo" id="temporada">
        Esta temporada
      </h2>
      <div className="columnas-temporada">
        {grupos.map(({ a, lista }) => (
          <div key={a}>
            <h3>
              <Link href={rutaCalendario(a)}>{TITULO[a]}</Link>
            </h3>
            {lista.length ? (
              <ul>
                {lista.map((e) => (
                  <li key={e.id} className={`cat-${e.categoria}`}>
                    <span className="punto-cat" aria-hidden />
                    <Link href={`/evento/${e.id}`}>{e.nombre}</Link>
                    <small>hasta el {fechaCorta(e.hasta)}</small>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="nota-pie">Nada destacado estos días.</p>
            )}
          </div>
        ))}
      </div>
      <p className="acciones-temporada">
        <Link href="/viaje" className="enlace-boton">
          Planifica un viaje →
        </Link>
        <Link href="/calendario" className="enlace-boton">
          Calendario del paisaje
        </Link>
        <Link href="/fauna" className="enlace-boton">
          Dónde ver fauna
        </Link>
      </p>
    </section>
  );
}
