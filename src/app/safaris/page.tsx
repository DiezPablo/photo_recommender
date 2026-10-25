import type { Metadata } from "next";
import Link from "next/link";
import { MESES } from "@/features/eventos/modelo";
import ExploradorSafaris from "@/features/safaris/componentes/ExploradorSafaris";
import {
  cargarMundo,
  cargarRecientes,
  cargarSafaris,
  enTemporada,
  nombreEspecieMundo,
  nombreTaxon,
  puntuacionAhora,
  slugEspecie,
} from "@/features/safaris/datos";
import { fechaLocal } from "@/lib/sol";

export const metadata: Metadata = {
  title: "Safaris",
  description:
    "Parques de safari de todo el mundo: cuándo ir, qué especies se ven (y qué se ha visto este mes), tipos de safari, tasas, alojamientos y consejos.",
};

export default function PaginaSafaris() {
  const datos = cargarSafaris();
  const recientes = cargarRecientes();
  const mesHoy = Number(fechaLocal(new Date()).slice(5, 7)) - 1;
  const parques = datos?.parques ?? [];
  const ahora = parques
    .filter((p) => enTemporada(p, mesHoy))
    .sort((a, b) => puntuacionAhora(b, mesHoy, recientes) - puntuacionAhora(a, mesHoy, recientes))
    .slice(0, 6);
  const mundo = cargarMundo();
  const total = mundo?.parques.length ?? parques.length;
  const paisesMundo = new Set((mundo?.parques ?? []).map((p) => p.pais)).size;
  const especies = Object.keys(mundo?.estrella ?? {})
    .map((k) => ({ clave: Number(k), nombre: nombreEspecieMundo(mundo!, k) }))
    .sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));
  return (
    <main className="calendario fauna safaris">
      <header className="titular">
        <p className="rotulo">
          {total.toLocaleString("es-ES")} parques y reservas · {paisesMundo || new Set(parques.map((p) => p.pais)).size}{" "}
          países · Wikidata, GBIF, iNaturalist y OpenStreetMap
        </p>
        <h1>Safaris por el mundo</h1>
        <nav className="pestanas" aria-label="Safaris">
          <Link href="/safaris" aria-current="page">
            Parques
          </Link>
          <Link href="/safaris/especie">Especies</Link>
          <Link href="/safaris/guia">Cómo organizarlo</Link>
        </nav>
        <p className="entradilla">
          Todos los parques nacionales y reservas del mundo con fauna registrada: qué se ve y cuándo, lo que han visto
          los observadores en el último mes, cómo llegar (aeropuertos y pistas de aterrizaje), puertas, operadores
          locales y alojamientos con su web. Sin intermediarios ni comisiones: reservas directamente con el parque, el
          lodge o el operador.
        </p>
      </header>

      {ahora.length > 0 && (
        <section className="seccion">
          <h2 className="rotulo">Destacados en buena época ahora, en {MESES[mesHoy]}</h2>
          <ul className="lista-cercanos">
            {ahora.map((p) => {
              const r = recientes?.parques[p.id];
              const top = r?.mamiferos.slice(0, 3).map((m) => m.nombre ?? m.cientifico);
              return (
                <li key={p.id}>
                  <Link href={`/safaris/${p.id}`}>{p.nombre}</Link>
                  <small>
                    {p.pais}
                    {top?.length ? ` · visto este mes: ${top.join(", ")}` : ""}
                  </small>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {parques.length ? (
        <>
          <ExploradorSafaris
            especies={especies}
            mesHoy={mesHoy}
            fotos={Object.fromEntries(parques.filter((p) => p.foto).map((p) => [p.id, p.foto!.url]))}
          />
          <noscript>
            <ul className="lista-cercanos">
              {parques.map((p) => (
                <li key={p.id}>
                  <Link href={`/safaris/${p.id}`}>{p.nombre}</Link>
                  <small>{p.pais}</small>
                </li>
              ))}
            </ul>
          </noscript>
          <section className="seccion">
            <h2 className="rotulo">Por especie</h2>
            <p className="enlaces-especies">
              {(datos?.especies ?? []).slice(0, 24).map((e) => (
                <Link key={e.taxon} href={`/safaris/especie/${slugEspecie(e)}`}>
                  {nombreTaxon(e)}
                </Link>
              ))}
            </p>
          </section>
        </>
      ) : (
        <p>Los safaris aún no están disponibles.</p>
      )}
    </main>
  );
}
