// En la ficha de un spot o de un evento: lo habitual cada mes según cinco años de ERA5.
import TablaClima from "@/features/clima/componentes/TablaClima";
import { cargarClima, climaDe, deCada, mejorMes, NOMBRE_SERIE, type SerieClima } from "@/features/clima/datos";
import { MESES } from "@/features/eventos/modelo";

export default function ClimaSpot({
  lat,
  lon,
  mes,
  titulo = "Qué esperar cada mes",
}: {
  lat: number;
  lon: number;
  /** mes a destacar (0-11) */
  mes?: number;
  titulo?: string;
}) {
  const clima = cargarClima();
  const p = climaDe(clima, lat, lon);
  if (!clima || !p) return null;
  const destacados = (["atardecer", "amanecer", "noche"] as SerieClima[])
    .map((s) => ({ s, m: mejorMes(p, s) }))
    .filter((x): x is { s: SerieClima; m: number } => x.m !== null);
  return (
    <section className="seccion clima-spot">
      <h2 className="rotulo">{titulo}</h2>
      {mes !== undefined && (
        <p>
          En {MESES[mes]}, lo habitual aquí:{" "}
          {(["atardecer", "amanecer", "noche", "niebla"] as SerieClima[])
            .map((s) => `${NOMBRE_SERIE[s].toLowerCase()}, ${deCada(p[s][mes] ?? 0)}`)
            .join("; ")}
          .
        </p>
      )}
      <TablaClima punto={p} mesActual={mes} />
      <p className="mejores-meses">
        {destacados.map(({ s, m }) => (
          <span key={s}>
            {NOMBRE_SERIE[s]}: <b>{MESES[m]}</b> ({p[s][m]} %)
          </span>
        ))}
      </p>
      <p className="nota-pie">
        Porcentaje de días de cada mes entre {clima.desde.slice(0, 4)} y {clima.hasta.slice(0, 4)} con nota de{" "}
        {clima.nota_buena} o más (con los mismos modelos que la previsión), con al menos {clima.horas_noche} h seguidas
        sin nubes de noche, o con niebla al amanecer. Reanálisis ERA5 a ~30 km: describe la zona, no cada valle.
      </p>
    </section>
  );
}
