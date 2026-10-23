// Línea temporal del día en un spot: el cielo (noche, hora azul, dorada, día) de 4:00 a 7:00 del día
// siguiente (para que quepa la noche entera) y,
// encima, cuándo ocurre cada salida con su nota. Sin JavaScript.
import { calificacion, type Dia, type Momento, motivos, NOMBRE_MOMENTO } from "@/lib/modelo";
import Cifra from "./Cifra";

const INI = 4 * 60;
const FIN = INI + 27 * 60;
const HORAS = [4, 8, 12, 16, 20, 24, 28];

/** "HH:MM" → minutos desde las 0:00 del día. De noche (astro, Vía Láctea) lo de antes de mediodía es
 * la madrugada siguiente; si no, solo lo de antes de las 4:00. */
function minutos(h: string | null | undefined, tras?: number, noche = false): number | null {
  const m = h?.match(/(\d{1,2}):(\d{2})/);
  if (!m) return null;
  let v = Number(m[1]) * 60 + Number(m[2]);
  if (v < (noche ? 12 * 60 : INI) || (tras !== undefined && v < tras)) v += 24 * 60;
  return Math.min(Math.max(v, INI), FIN);
}
const pct = (v: number) => `${(((v - INI) / (FIN - INI)) * 100).toFixed(2)}%`;

interface Evento {
  momento: Momento;
  ini: number;
  fin?: number;
  hora: string;
  nota: number;
  porque: string;
}

export default function PlanDelDia({ dia }: { dia: Dia }) {
  const s = dia.sol;
  const n = dia.noche;
  // Tramos del cielo, en orden; lo que no se conoce (latitudes extremas) se queda en "día"
  const cortes: [string, number | null][] = [
    ["noche", minutos(s.azul_manana?.[0])],
    ["azul", minutos(s.dorada_manana?.[0])],
    ["dorada", minutos(s.dorada_manana?.[1])],
    ["dia", minutos(s.dorada_tarde?.[0])],
    ["dorada", minutos(s.azul_tarde?.[0])],
    ["azul", minutos(s.azul_tarde?.[1])],
  ];
  const paradas: string[] = [];
  let previo = INI;
  for (const [tramo, hasta] of cortes) {
    if (hasta === null) continue;
    paradas.push(`var(--cielo-${tramo}) ${pct(previo)} ${pct(hasta)}`);
    previo = hasta;
  }
  paradas.push(`var(--cielo-noche) ${pct(previo)} 100%`);

  const ev: Evento[] = [];
  const add = (momento: Momento, ini: number | null, hora: string, fin?: number | null) => {
    const nota = dia.notas[momento];
    if (ini === null || !nota) return;
    ev.push({ momento, ini, fin: fin ?? undefined, hora, nota: nota.nota, porque: motivos(nota, 1).map((m) => m.texto).join("") });
  };
  const hAm = s.amanecer_relieve ?? s.amanecer;
  const hAt = s.atardecer_relieve ?? s.atardecer;
  add("niebla", minutos(s.azul_manana?.[0] ?? hAm), `madrugada, antes de ${hAm ?? "amanecer"}`);
  add("amanecer", minutos(hAm), hAm ?? "—");
  add("atardecer", minutos(hAt), hAt ?? "—");
  const e = n.luna.evento;
  if (e) add("luna", minutos(e.hora), `${e.tipo === "salida" ? "sale" : "se pone"} ${e.hora}`);
  const v = dia.notas.astro?.modelo?.ventana as [string, string] | undefined;
  const a0 = minutos(v?.[0] ?? n.ini, undefined, true);
  if (a0 !== null) {
    // la ventana puede acabar en "fin de la noche"
    const finV = v && /\d:\d\d/.test(v[1]) ? v[1] : n.fin;
    add("astro", a0, v ? `mejor ventana ${v[0]}–${finV}` : `${n.ini}–${n.fin}`, minutos(finV, a0, true));
  }
  ev.sort((x, y) => x.ini - y.ini);
  const vl = n.via_lactea.tramos
    .map((t) => [minutos(t[0], undefined, true), minutos(t[1], minutos(t[0], undefined, true) ?? undefined, true)] as const)
    .filter((t): t is readonly [number, number] => t[0] !== null && t[1] !== null);

  return (
    <section className="seccion plan" aria-label="Plan del día">
      <h2 className="rotulo">El día, hora a hora</h2>
      <div className="plan-eje" aria-hidden="true">
        <div className="plan-cielo" style={{ background: `linear-gradient(90deg, ${paradas.join(", ")})` }}>
          {vl.map(([a, b], i) => (
            <span key={i} className="plan-vl" style={{ left: pct(a), width: `calc(${pct(b)} - ${pct(a)})` }} />
          ))}
          {ev.map((x) => x.fin !== undefined
            ? <span key={x.momento} className={`plan-tramo ${calificacion(x.nota).clase}`} style={{ left: pct(x.ini), width: `calc(${pct(x.fin)} - ${pct(x.ini)})` }} />
            : <span key={x.momento} className={`plan-punto ${calificacion(x.nota).clase}`} style={{ left: pct(x.ini) }} />)}
        </div>
        <div className="plan-horas">
          {HORAS.map((h) => <span key={h} style={{ left: pct(h * 60) }}>{h % 24}h</span>)}
        </div>
        <div className="plan-leyenda">
          <span><i style={{ background: "var(--cielo-azul)" }} />Hora azul</span>
          <span><i style={{ background: "var(--cielo-dorada)" }} />Hora dorada</span>
          {vl.length > 0 && <span><i style={{ background: "var(--vl)" }} />Vía Láctea sobre 10°</span>}
        </div>
      </div>
      <ol className="plan-lista">
        {ev.map((x) => (
          <li key={x.momento}>
            <a href={`#nota-${x.momento}`}>
              <span className="plan-hora">{x.hora.match(/\d{1,2}:\d{2}/)?.[0] ?? "—"}</span>
              <Cifra nota={x.nota} />
              <span>
                <b>{NOMBRE_MOMENTO[x.momento]}</b>
                <small>{x.hora}{x.porque ? `. ${x.porque}` : ""}</small>
              </span>
            </a>
          </li>
        ))}
      </ol>
    </section>
  );
}
