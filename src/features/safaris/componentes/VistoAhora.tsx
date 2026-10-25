"use client";
// «Visto en los últimos 30 días»: se pide a iNaturalist en directo (su API admite peticiones del navegador) y,
// si no responde, se muestra lo que trajo la última actualización de los datos.
import Link from "next/link";
import { useEffect, useState } from "react";
import { slugEspecie } from "@/features/safaris/modelo";

interface Fila {
  taxon: number;
  cientifico: string;
  nombre: string | null;
  n: number;
  foto?: string | null;
}

const DIAS = 30;

export default function VistoAhora({
  lat,
  lon,
  radioKm,
  respaldo,
  conFicha,
}: {
  lat: number;
  lon: number;
  radioKm: number;
  respaldo: Fila[];
  /** taxones con página propia en /safaris/especie */
  conFicha: number[];
}) {
  const [filas, setFilas] = useState<Fila[] | null>(null);
  const [directo, setDirecto] = useState(false);

  useEffect(() => {
    const desde = new Date(Date.now() - DIAS * 86400000).toISOString().slice(0, 10);
    const url =
      `https://api.inaturalist.org/v1/observations/species_counts?lat=${lat}&lng=${lon}&radius=${radioKm}` +
      `&d1=${desde}&iconic_taxa=Mammalia,Aves,Reptilia&verifiable=true&locale=es&per_page=12`;
    let vivo = true;
    fetch(url)
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((d) => {
        if (!vivo) return;
        setFilas(
          d.results.map(
            (r: {
              count: number;
              taxon: {
                id: number;
                name: string;
                preferred_common_name?: string;
                default_photo?: { square_url?: string; license_code?: string };
              };
            }) => ({
              taxon: r.taxon.id,
              cientifico: r.taxon.name,
              nombre: r.taxon.preferred_common_name ?? null,
              n: r.count,
              foto: r.taxon.default_photo?.license_code ? r.taxon.default_photo.square_url : null,
            }),
          ),
        );
        setDirecto(true);
      })
      .catch(() => vivo && setFilas(respaldo));
    return () => {
      vivo = false;
    };
  }, [lat, lon, radioKm, respaldo]);

  const lista = filas ?? respaldo;
  return (
    <section className="seccion visto-ahora">
      <h2 className="rotulo">Visto en los últimos {DIAS} días</h2>
      {lista.length ? (
        <ul className="lista-visto">
          {lista.map((f) => (
            <li key={f.taxon}>
              {f.foto ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={f.foto} alt="" width={40} height={40} loading="lazy" />
              ) : (
                <span className="sin-foto" aria-hidden />
              )}
              <span>
                {conFicha.includes(f.taxon) ? (
                  <Link href={`/safaris/especie/${slugEspecie(f)}`}>{f.nombre ?? f.cientifico}</Link>
                ) : (
                  (f.nombre ?? f.cientifico)
                )}{" "}
                <small>
                  {f.n} {f.n === 1 ? "observación" : "observaciones"}
                </small>
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p>{filas === null ? "Consultando iNaturalist…" : "Nadie ha subido observaciones este mes."}</p>
      )}
      <p className="nota-pie">
        Observaciones de iNaturalist {directo ? "en directo" : "de la última actualización"}: dicen qué se está viendo
        estos días, aunque dependen de cuánta gente sube fotos.
      </p>
    </section>
  );
}
