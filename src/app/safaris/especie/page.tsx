import type { Metadata } from "next";
import Link from "next/link";
import { cargarSafaris, getParque, nombreTaxon, slugEspecie } from "@/features/safaris/datos";

export const metadata: Metadata = {
  title: "Especies de safari",
  description: "Dónde ver león, leopardo, gorila, tigre, jaguar, oso polar y otras especies en los parques del mundo.",
};

export default function PaginaEspeciesSafari() {
  const especies = cargarSafaris()?.especies ?? [];
  return (
    <main className="calendario fauna safaris">
      <header className="titular">
        <p className="rotulo">{especies.length} especies · iNaturalist</p>
        <h1>Qué quieres ver</h1>
        <nav className="pestanas" aria-label="Safaris">
          <Link href="/safaris">Parques</Link>
          <Link href="/safaris/especie" aria-current="page">
            Especies
          </Link>
          <Link href="/safaris/guia">Cómo organizarlo</Link>
        </nav>
        <p className="entradilla">
          Para cada especie, los parques donde más se ha observado. Elige el animal y luego la época.
        </p>
      </header>
      <ul className="rejilla-especies">
        {especies.map((e) => (
          <li key={e.taxon} className="tarjeta-especie">
            {e.foto ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={e.foto.url} alt="" loading="lazy" decoding="async" />
            ) : (
              <span className="sin-foto" aria-hidden />
            )}
            <div>
              <h3>
                <Link href={`/safaris/especie/${slugEspecie(e)}`}>{nombreTaxon(e)}</Link>
              </h3>
              <p>
                <i>{e.cientifico}</i>
              </p>
              <p className="meta">
                {e.parques
                  .slice(0, 3)
                  .map((x) => getParque(x.id)?.nombre)
                  .filter(Boolean)
                  .join(", ") || "Pocas observaciones en los parques"}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}
