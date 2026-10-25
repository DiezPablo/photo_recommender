// En la ficha de una ruta: los spots por los que pasa, en orden, con su nota de hoy.
import Link from "next/link";
import Cifra from "@/ui/Cifra";
import { pasoPor } from "@/features/rutas/cima";
import { duracion, type Ruta } from "@/features/rutas/modelo";
import { cargar, notaDe, NOMBRE_CORTO } from "@/features/spots/datos";

export default function SpotsEnRuta({ ruta: r }: { ruta: Ruta }) {
  const [oeste, sur, este, norte] = r.bbox;
  const m = 0.005;
  const enCamino = cargar()
    .spots.filter((s) => s.lat >= sur - m && s.lat <= norte + m && s.lon >= oeste - m && s.lon <= este + m)
    .map((s) => ({ s, paso: pasoPor(r, s.lat, s.lon) }))
    .filter((x): x is { s: (typeof x)["s"]; paso: NonNullable<(typeof x)["paso"]> } => x.paso !== null)
    .sort((a, b) => a.paso.km - b.paso.km);
  if (!enCamino.length) return null;
  return (
    <section className="seccion">
      <h2 className="rotulo">Spots en el camino</h2>
      <ol className="lista-cercanos">
        {enCamino.map(({ s, paso }) => {
          const hoy = notaDe(s.dias[0], "todos");
          return (
            <li key={s.id}>
              <Link href={`/spot/${s.id}`}>{s.nombre}</Link>
              <small>
                km {paso.km.toLocaleString("es-ES")} · {duracion(paso.horasIda)} desde la salida
                {hoy && (
                  <>
                    {" "}
                    · hoy, {NOMBRE_CORTO[hoy.momento].toLowerCase()} <Cifra nota={hoy.nota.nota} />
                  </>
                )}
              </small>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
