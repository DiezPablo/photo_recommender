// En la ficha de un spot o de un evento: lugares de observación de fauna cerca, con lo que más se ve.
import Link from "next/link";
import { faunaCerca, nombreEspecie } from "@/features/fauna/datos";

export default function FaunaCerca({
  lat,
  lon,
  km = 10,
  max = 3,
  titulo = "Fauna cerca",
}: {
  lat: number;
  lon: number;
  km?: number;
  max?: number;
  titulo?: string;
}) {
  const lista = faunaCerca(lat, lon, km).slice(0, max);
  if (!lista.length) return null;
  return (
    <section className="seccion">
      <h2 className="rotulo">{titulo}</h2>
      <ul className="lista-cercanos">
        {lista.map((l) => (
          <li key={l.id}>
            <Link href={`/fauna/${l.id}`}>{l.nombre}</Link>
            <small>
              a{" "}
              {l.km < 1
                ? `${Math.round(l.km * 1000)} m`
                : `${l.km.toLocaleString("es-ES", { maximumFractionDigits: 1 })} km`}{" "}
              · {l.especies.slice(0, 3).map(nombreEspecie).join(", ")}
            </small>
          </li>
        ))}
      </ul>
    </section>
  );
}
