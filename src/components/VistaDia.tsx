// Portada: filtros (enlaces normales, sin JavaScript), ranking y mapa del día elegido.
import Link from "next/link";
import { cargar, etiquetaDia, FILTROS, type Filtro, miniatura, MOMENTOS, NOMBRE_CORTO, NOMBRE_MOMENTO } from "@/lib/datos";
import { filasRanking, TOP_HTML, urlRanking } from "@/lib/ranking";
import Destacado from "./Destacado";
import { IconoMomento } from "./Iconos";
import Semana, { type Mejor } from "./Semana";
import Mapa from "./Mapa";
import Ranking from "./Ranking";

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
  const filas = filasRanking(d, filtro);
  const top = filas.slice(0, TOP_HTML);
  const fiab = spots[0].dias[d]?.fiabilidad ?? "alta";
  const et = etiquetaDia(fecha, d);
  const buenos = filas.filter((f) => f.nota >= 6.5).length;
  const mejores: Record<string, Mejor[]> = {};
  for (const m of MOMENTOS) {
    mejores[m] = informe.fechas.map((_, i) => {
      let b: Mejor = null;
      for (const s of spots) {
        const n = s.dias[i]?.notas[m]?.nota;
        if (n !== undefined && (!b || n > b.nota)) b = { nota: n, nombre: s.nombre };
      }
      return b;
    });
  }
  const primero = top[0];
  const fotoPrimero = primero ? miniatura(spots.find((s) => s.id === primero.id)?.descubierto?.galeria?.[0]?.url, 960) : null;

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
        <div className="columna">
          {primero && <Destacado f={primero} foto={fotoPrimero} dia={et.corto === "Hoy" || et.corto === "Mañana" ? et.corto.toLowerCase() : et.largo} />}
          <Semana fechas={informe.fechas} mejores={mejores} d={d} filtro={filtro} ruta={rutaDia} />
        </div>
        <Mapa
          puntos={top.map((f) => ({
            id: f.id, nombre: f.nombre, lat: f.lat, lon: f.lon, nota: f.nota, clase: f.clase,
            texto: `${NOMBRE_CORTO[f.momento]} · ${f.hora}`,
          }))}
          urlTodos={urlRanking(d, filtro)}
        />
        <section aria-label="Ranking" style={{ display: "grid", gap: 10 }}>
          <Ranking filas={top} total={filas.length} urlTodos={urlRanking(d, filtro)} mostrarMomento={filtro === "todos"}
            comunidades={[...new Set(filas.map((f) => f.ccaa).filter((c): c is string => !!c))].sort()} />
        </section>
      </main>
    </>
  );
}
