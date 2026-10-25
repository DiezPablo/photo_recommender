import type { Metadata } from "next";
import Link from "next/link";
import ExploradorFauna from "@/features/fauna/componentes/ExploradorFauna";
import { cargarFauna, nombreEspecie } from "@/features/fauna/datos";

export const metadata: Metadata = {
  title: "Fauna",
  description:
    "Observatorios de fauna de toda España con las especies que más se ven en cada uno y en qué meses (OpenStreetMap y GBIF).",
};

export default function PaginaFauna() {
  const fauna = cargarFauna();
  const lugares = fauna?.lugares ?? [];
  const comunidades = [...new Set(lugares.map((l) => l.ccaa))].sort((a, b) => a.localeCompare(b, "es"));
  return (
    <main className="calendario fauna">
      <header className="titular">
        <p className="rotulo">{lugares.length.toLocaleString("es-ES")} lugares · OpenStreetMap y GBIF</p>
        <h1>Dónde ver fauna</h1>
        <nav className="pestanas" aria-label="Fauna">
          <Link href="/fauna" aria-current="page">
            Lugares
          </Link>
          <Link href="/fauna/calendario">Calendario de fauna</Link>
        </nav>
        <p className="entradilla">
          Observatorios de toda España con las especies que más se observan alrededor y en qué meses, según cientos de
          miles de registros de observadores (eBird, iNaturalist, Observation.org…). Respeta las distancias y no salgas
          de los caminos.
        </p>
      </header>
      {lugares.length ? (
        <>
          <ExploradorFauna comunidades={comunidades} />
          <noscript>
            <ul className="lista-cercanos">
              {lugares.slice(0, 40).map((l) => (
                <li key={l.id}>
                  <Link href={`/fauna/${l.id}`}>{l.nombre}</Link>
                  <small>
                    {l.provincia} · {l.especies.slice(0, 4).map(nombreEspecie).join(", ")}
                  </small>
                </li>
              ))}
            </ul>
          </noscript>
        </>
      ) : (
        <p>Los lugares de fauna aún no están disponibles.</p>
      )}
    </main>
  );
}
