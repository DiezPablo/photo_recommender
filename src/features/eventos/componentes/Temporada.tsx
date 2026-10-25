// En la portada: qué está en su mejor momento estos días y accesos al planificador y al calendario.
import Link from "next/link";
import { activoEn, cargarEventos, fechaCorta } from "@/features/eventos/datos";

/** Días entre dos fechas MM-DD dentro del año (el más corto, cruzando año si hace falta). */
function diasEntre(a: string, b: string): number {
  const d = (x: string) => Date.UTC(2027, Number(x.slice(0, 2)) - 1, Number(x.slice(3, 5))) / 864e5;
  const n = Math.abs(d(a) - d(b));
  return Math.min(n, 365 - n);
}

export default function Temporada({ hoy, max = 4 }: { hoy: string; max?: number }) {
  const eventos = cargarEventos();
  if (!eventos) return null;
  const md = hoy.slice(5);
  // los más cerca de su mejor momento, sin más de dos de la misma categoría (que no salga solo otoño)
  const porCategoria = new Map<string, number>();
  const ahora = eventos.naturaleza
    .filter((e) => activoEn(e, hoy))
    .sort((a, b) => diasEntre(a.pico, md) - diasEntre(b.pico, md))
    .filter((e) => {
      const n = porCategoria.get(e.categoria) ?? 0;
      porCategoria.set(e.categoria, n + 1);
      return n < 2;
    })
    .slice(0, max);
  return (
    <section className="temporada-portada" aria-labelledby="temporada">
      <h2 className="rotulo" id="temporada">
        Esta temporada
      </h2>
      {ahora.length > 0 && (
        <ul>
          {ahora.map((e) => (
            <li key={e.id} className={`cat-${e.categoria}`}>
              <span className="punto-cat" aria-hidden />
              <Link href={`/evento/${e.id}`}>{e.nombre}</Link>
              <small>hasta el {fechaCorta(e.hasta)}</small>
            </li>
          ))}
        </ul>
      )}
      <p className="acciones-temporada">
        <Link href="/viaje" className="enlace-boton">
          Planifica un viaje →
        </Link>
        <Link href="/calendario" className="enlace-boton">
          Calendario del año
        </Link>
      </p>
    </section>
  );
}
