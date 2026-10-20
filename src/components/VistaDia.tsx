// Portada: filtros (enlaces normales, sin JavaScript), ranking y mapa del día elegido.
import Link from "next/link";
import {
  calificacion, cargar, etiquetaDia, FILTROS, type Filtro, horaDe, motivos, NOMBRE_CORTO, NOMBRE_MOMENTO, notaDe,
} from "@/lib/datos";
import { IconoMomento } from "./Iconos";
import Mapa from "./Mapa";
import Ranking from "./Ranking";
import type { FilaRanking } from "./tipos";

export function rutaDia(d: number, f: Filtro) {
  return d === 0 && f === "todos" ? "/" : `/dia/${d}/${f}`;
}

const TEXTO_FIABILIDAD = {
  alta: "Previsión fiable",
  media: "Fiabilidad media: revisa la previsión la víspera",
  baja: "Fiabilidad baja: a más de 3 días las nubes son poco fiables",
};

export default function VistaDia({ d, filtro }: { d: number; filtro: Filtro }) {
  const { informe, spots } = cargar();
  if (!informe || spots.length === 0) {
    return (
      <main className="portada">
        <p className="vacio">Aún no hay datos publicados. El primer cálculo se hace en GitHub Actions.</p>
      </main>
    );
  }
  const fecha = informe.fechas[d];
  const filas: FilaRanking[] = spots
    .map((s) => {
      const dia = s.dias[d];
      const n = notaDe(dia, filtro);
      if (!dia || !n) return null;
      return {
        id: s.id, nombre: s.nombre, lat: s.lat, lon: s.lon, tipo: s.tipo,
        nota: n.nota.nota, clase: calificacion(n.nota.nota).clase, momento: n.momento,
        hora: horaDe(dia, n.momento),
        motivos: motivos(n.nota).map((m) => m.texto),
      };
    })
    .filter((f): f is FilaRanking => f !== null)
    .sort((a, b) => b.nota - a.nota || a.nombre.localeCompare(b.nombre));
  const fiab = spots[0].dias[d]?.fiabilidad ?? "alta";
  const et = etiquetaDia(fecha, d);
  const buenos = filas.filter((f) => f.nota >= 6.5).length;

  return (
    <>
      <nav className="filtros" aria-label="Filtros">
        <div className="fila-chips" aria-label="Día">
          {informe.fechas.map((f, i) => {
            const e = etiquetaDia(f, i);
            return (
              <Link key={f} href={rutaDia(i, filtro)} className="chip" aria-current={i === d ? "page" : undefined}>
                {e.corto} <small>{e.largo.split(" ").slice(1).join(" ")}</small>
              </Link>
            );
          })}
        </div>
        <div className="fila-chips" aria-label="Tipo de salida">
          {FILTROS.map((f) => (
            <Link key={f} href={rutaDia(d, f)} className="chip" aria-current={f === filtro ? "page" : undefined}>
              <IconoMomento momento={f} size={16} /> {NOMBRE_CORTO[f]}
            </Link>
          ))}
        </div>
      </nav>
      <main className="portada">
        <div className="resumen-dia">
          <h1>
            {filtro === "todos" ? "Lo mejor" : NOMBRE_MOMENTO[filtro]} · <span style={{ textTransform: "capitalize" }}>{et.largo}</span>
          </h1>
          <span>
            {buenos > 0 ? `${buenos} ${buenos === 1 ? "spot con buena nota" : "spots con buena nota"}` : "Ningún spot destaca"} de {filas.length}
          </span>
          <span className={`fiabilidad ${fiab}`}>{TEXTO_FIABILIDAD[fiab]}</span>
        </div>
        <Mapa
          puntos={filas.map((f) => ({
            id: f.id, nombre: f.nombre, lat: f.lat, lon: f.lon, nota: f.nota, clase: f.clase,
            texto: `${NOMBRE_CORTO[f.momento]} · ${f.hora}`,
          }))}
        />
        <section aria-label="Ranking" style={{ display: "grid", gap: 10 }}>
          <Ranking filas={filas} mostrarMomento={filtro === "todos"} />
        </section>
      </main>
    </>
  );
}
