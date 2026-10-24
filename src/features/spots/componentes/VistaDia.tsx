// Portada: titular del día, tabla de los próximos días (que hace de filtro), ranking y mapa.
import { cargar, etiquetaDia, FILTROS, type Filtro, miniatura, NOMBRE_MOMENTO, notaDe } from "@/features/spots/datos";
import { filasRanking, TOP_HTML, urlRanking } from "@/features/spots/ranking";
import Almanaque, { type Mejor } from "@/features/spots/componentes/Almanaque";
import Destacado from "@/features/spots/componentes/Destacado";
import Mapa from "@/features/spots/componentes/MapaSpots";
import Ranking from "@/features/spots/componentes/Ranking";

export function rutaDia(d: number, f: Filtro) {
  return d === 0 && f === "todos" ? "/" : `/dia/${d}/${f}`;
}

const TEXTO_FIABILIDAD = {
  alta: "previsión fiable",
  media: "fiabilidad media: revísalo la víspera",
  baja: "fiabilidad baja: a más de 3 días las nubes cambian",
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
  const filas = filasRanking(d, filtro);
  const top = filas.slice(0, TOP_HTML);
  const fiab = spots[0].dias[d]?.fiabilidad ?? "alta";
  const et = etiquetaDia(informe.fechas[d], d);
  const buenos = filas.filter((f) => f.nota >= 6.5).length;
  const mejores: Record<string, Mejor[]> = {};
  for (const m of FILTROS) {
    mejores[m] = informe.fechas.map((_, i) => {
      let b: Mejor = null;
      let excelentes = 0;
      for (const s of spots) {
        const n = notaDe(s.dias[i], m)?.nota.nota;
        if (n === undefined) continue;
        if (n >= 8) excelentes++;
        if (!b || n > b.nota) b = { nota: n, nombre: s.nombre, excelentes: 0 };
      }
      return b && { ...b, excelentes };
    });
  }
  const primero = top[0];
  const credito = primero ? (spots.find((s) => s.id === primero.id)?.descubierto?.galeria?.[0] ?? null) : null;
  const cuando = d === 0 ? "hoy" : d === 1 ? "mañana" : `el ${et.largo}`;

  return (
    <main className="portada">
      <div className="columna">
        <header className="titular">
          <p className="rotulo">
            {et.largo} · {buenos} de {filas.length} spots con buena nota · {TEXTO_FIABILIDAD[fiab]}
          </p>
          <h1>{filtro === "todos" ? `Lo mejor de ${cuando}` : `${NOMBRE_MOMENTO[filtro]}, ${cuando}`}</h1>
        </header>
        {primero && <Destacado f={primero} foto={miniatura(credito?.url, 960)} credito={credito} />}
        <Almanaque fechas={informe.fechas} mejores={mejores} d={d} filtro={filtro} ruta={rutaDia} />
        <section aria-label="Ranking" className="bloque-ranking">
          <h2 className="rotulo">
            Ranking · {NOMBRE_MOMENTO[filtro].toLowerCase()} · {cuando}
          </h2>
          <Ranking
            filas={top}
            total={filas.length}
            urlTodos={urlRanking(d, filtro)}
            mostrarMomento={filtro === "todos"}
            comunidades={[...new Set(filas.map((f) => f.ccaa).filter((c): c is string => !!c))].sort()}
          />
        </section>
      </div>
      <Mapa
        puntos={top.map((f) => ({
          id: f.id,
          nombre: f.nombre,
          lat: f.lat,
          lon: f.lon,
          nota: f.nota,
          clase: f.clase,
          texto: `${NOMBRE_MOMENTO[f.momento]} · ${f.hora}`,
        }))}
        urlTodos={urlRanking(d, filtro)}
      />
    </main>
  );
}
