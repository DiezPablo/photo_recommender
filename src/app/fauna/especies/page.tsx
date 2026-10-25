import type { Metadata } from "next";
import Link from "next/link";
import { MESES } from "@/features/eventos/modelo";
import PestanasFauna from "@/features/fauna/componentes/PestanasFauna";
import { cargarEspecies, GRUPOS, type Grupo, mesesFaciles, provinciasDe, resumirMeses } from "@/features/fauna/datos";

export const metadata: Metadata = {
  title: "Especies",
  description:
    "Dónde y cuándo ver lince, oso, lobo, quebrantahuesos, grullas, orcas y otras especies emblemáticas de España, según las observaciones de GBIF.",
};

export default function PaginaEspecies() {
  const especies = cargarEspecies()?.especies ?? [];
  const grupos = (Object.keys(GRUPOS) as Grupo[])
    .map((g) => [g, especies.filter((e) => e.grupo === g)] as const)
    .filter(([, lista]) => lista.length);
  return (
    <main className="calendario fauna">
      <header className="titular">
        <p className="rotulo">{especies.length} especies · GBIF</p>
        <h1>Dónde ver cada especie</h1>
        <PestanasFauna actual="/fauna/especies" />
        <p className="entradilla">
          Lince, oso, lobo, quebrantahuesos, grullas, cetáceos… En qué zonas de España se han observado más y en qué
          meses es más fácil verlos, con miles de observaciones de 2016 a 2025. Muestra dónde hay observaciones, no un
          censo: para las especies sensibles la ubicación es aproximada (~25 km).
        </p>
      </header>
      {grupos.length ? (
        grupos.map(([g, lista]) => (
          <section key={g} className="seccion">
            <h2 className="rotulo">{GRUPOS[g]}</h2>
            <ul className="rejilla-especies">
              {lista.map((e) => {
                const faciles = mesesFaciles(e);
                return (
                  <li key={e.id} className="tarjeta-especie">
                    {e.foto ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={e.foto.url} alt="" loading="lazy" decoding="async" />
                    ) : (
                      <span className="sin-foto" aria-hidden />
                    )}
                    <div>
                      <h3>
                        <Link href={`/fauna/especies/${e.id}`}>{e.nombre}</Link>
                      </h3>
                      <p>
                        <i>{e.cientifico}</i>
                      </p>
                      <p className="meta">{provinciasDe(e, 3).join(", ") || "Pocas observaciones"}</p>
                      <p className="meta">
                        {faciles.length ? `Mejor: ${resumirMeses(faciles, MESES)}` : "Todo el año"}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>
        ))
      ) : (
        <p>Las especies aún no están disponibles.</p>
      )}
    </main>
  );
}
