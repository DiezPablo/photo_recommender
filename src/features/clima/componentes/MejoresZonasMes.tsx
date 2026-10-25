// En el calendario de un mes: dónde suele haber más atardeceres buenos y más noches despejadas ese mes, con un
// spot de cada zona como referencia.
import Link from "next/link";
import { cargarClima, climaDe, deCada, NOMBRE_SERIE, type SerieClima } from "@/features/clima/datos";
import { cargar } from "@/features/spots/datos";
import { MESES } from "@/features/eventos/modelo";

const SERIES_MES: SerieClima[] = ["atardecer", "amanecer", "noche"];

export default function MejoresZonasMes({ mes, cuantas = 5 }: { mes: number; cuantas?: number }) {
  const clima = cargarClima();
  if (!clima) return null;
  // cada spot en su punto de la rejilla; por zona, el spot con más fotos en Commons como referencia
  const zonas = new Map<
    string,
    { pct: Record<SerieClima, number>; spot: { id: string; nombre: string; provincia?: string | null; peso: number } }
  >();
  for (const s of cargar().spots) {
    const p = climaDe(clima, s.lat, s.lon);
    if (!p) continue;
    const clave = `${p.lat}_${p.lon}`;
    const peso = s.descubierto?.fotos ?? 0;
    const actual = zonas.get(clave);
    if (!actual || peso > actual.spot.peso) {
      zonas.set(clave, {
        pct: {
          atardecer: p.atardecer[mes] ?? 0,
          amanecer: p.amanecer[mes] ?? 0,
          noche: p.noche[mes] ?? 0,
          niebla: p.niebla[mes] ?? 0,
        },
        spot: { id: s.id, nombre: s.nombre, provincia: s.provincia, peso },
      });
    }
  }
  const lista = [...zonas.values()];
  return (
    <section className="seccion mejores-zonas" aria-labelledby="zonas-mes">
      <h2 className="rotulo" id="zonas-mes">
        Dónde suele ir mejor en {MESES[mes]}
      </h2>
      <div className="rejilla-zonas">
        {SERIES_MES.map((s) => (
          <div key={s}>
            <h3>{NOMBRE_SERIE[s]}</h3>
            <ol>
              {[...lista]
                .sort((a, b) => b.pct[s] - a.pct[s])
                .slice(0, cuantas)
                .map((z) => (
                  <li key={z.spot.id}>
                    <Link href={`/spot/${z.spot.id}`}>{z.spot.nombre}</Link>
                    <small>
                      {z.spot.provincia ? `${z.spot.provincia} · ` : ""}
                      {deCada(z.pct[s])} ({z.pct[s]} %)
                    </small>
                  </li>
                ))}
            </ol>
          </div>
        ))}
      </div>
      <p className="nota-pie">
        Frecuencia en {clima.desde.slice(0, 4)}-{clima.hasta.slice(0, 4)} (ERA5) en la zona de cada spot. Para los
        próximos días manda la previsión.
      </p>
    </section>
  );
}
