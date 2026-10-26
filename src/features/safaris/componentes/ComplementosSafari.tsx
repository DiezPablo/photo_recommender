// Dos piezas para planificar: los «cinco grandes» que se han observado en el parque (solo en África) y los
// parques cercanos con los que combinarlo, con la buena época en común y el tiempo aproximado por carretera.
import Link from "next/link";
import { distanciaKm, MESES } from "@/features/eventos/modelo";
import { buenaEpoca, type Mundo, type ParqueMundo } from "@/features/safaris/modelo";

const CINCO_GRANDES: [string, string][] = [
  ["León", "Panthera leo"],
  ["Leopardo", "Panthera pardus"],
  ["Elefante", "Loxodonta africana"],
  ["Búfalo", "Syncerus caffer"],
  ["Rinoceronte negro", "Diceros bicornis"],
  ["Rinoceronte blanco", "Ceratotherium simum"],
];
const MIN_OBS = 5;
const MAX_KM = 350;
// Por pistas y carreteras de parque: ~1,3 km de camino por km en línea recta y ~45 km/h de media
const KM_CAMINO = 1.3;
const KMH = 45;

function epocaDe(p: ParqueMundo): number[] {
  return buenaEpoca({ la: p.lat, sec: p.meses_secos, ep: p.epoca?.meses }) ?? [];
}

export function CincoGrandes({ p, mundo }: { p: ParqueMundo; mundo: Mundo }) {
  const clave = Object.fromEntries(Object.entries(mundo.estrella).map(([k, c]) => [c, k]));
  const filas = CINCO_GRANDES.map(([nombre, cientifico]) => ({
    nombre,
    n: p.estrella[clave[cientifico] ?? ""] ?? 0,
  }));
  if (filas.every((f) => f.n < MIN_OBS)) return null;
  const vistos = filas.filter((f) => f.n >= MIN_OBS).length;
  return (
    <section className="seccion">
      <h2 className="rotulo">Los cinco grandes</h2>
      <ul className="cinco-grandes">
        {filas.map((f) => (
          <li key={f.nombre} className={f.n >= MIN_OBS ? "si" : "no"}>
            <span aria-hidden>{f.n >= MIN_OBS ? "✓" : "–"}</span> {f.nombre}
            <small>{f.n >= MIN_OBS ? `${f.n.toLocaleString("es-ES")} obs.` : "sin registros"}</small>
          </li>
        ))}
      </ul>
      <p className="nota-pie">
        {vistos >= 5
          ? "Aquí se han observado los cinco grandes (con alguno de los dos rinocerontes)."
          : "Observaciones en GBIF desde 2010: un «sin registros» no garantiza que no esté, pero sí que es difícil."}
      </p>
    </section>
  );
}

export function CombinaCon({ p, mundo, nombre }: { p: ParqueMundo; mundo: Mundo; nombre: string }) {
  const propia = epocaDe(p);
  const cerca = mundo.parques
    .filter((x) => x.id !== p.id && x.puntuacion >= 80)
    .map((x) => {
      const km = distanciaKm(p, x);
      const comun = propia.filter((m) => epocaDe(x).includes(m));
      return { x, km, comun };
    })
    .filter((c) => c.km <= MAX_KM && c.km > 5)
    .sort((a, b) => Number(b.comun.length > 0) - Number(a.comun.length > 0) || a.km - b.km)
    .slice(0, 6);
  if (!cerca.length) return null;
  return (
    <section className="seccion">
      <h2 className="rotulo">Combínalo con</h2>
      <ul className="lista-cercanos">
        {cerca.map(({ x, km, comun }) => {
          const horas = (km * KM_CAMINO) / KMH;
          return (
            <li key={x.id}>
              <Link href={`/safaris/${x.id}`}>{x.nombre}</Link>
              <small>
                a {Math.round(km)} km en línea recta · unas {horas < 1 ? "1" : Math.round(horas)} h por carretera
                {comun.length > 0
                  ? ` · buena época también en ${comun.map((m) => MESES[m - 1]).join(", ")}`
                  : " · otra época"}
              </small>
            </li>
          );
        })}
      </ul>
      <p className="nota-pie">
        Las distancias engañan: en pistas de tierra se va despacio, así que los tiempos son orientativos. Si hay pista
        de aterrizaje en los dos parques, la avioneta ahorra un día de coche. Mejor 3-4 noches por parque que cambiar
        cada día desde {nombre}.
      </p>
    </section>
  );
}
