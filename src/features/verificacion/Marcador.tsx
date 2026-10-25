// «Cuánto acierta»: lo previsto el día anterior para ~35 aeropuertos frente a lo que observaron (METAR),
// últimos 30 días. Solo servidor; sin datos suficientes no se muestra.
import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

interface MarcadorDatos {
  desde: string;
  hasta: string;
  casos: number;
  aeropuertos: number;
  niebla: { observadas: number; detectadas: number; avisos: number; avisos_acertados: number; umbral: number };
  atardecer_cubierto: { acierto: number | null; persistencia: number | null };
  noche_despejada: { acierto: number | null; persistencia: number | null };
}

const MIN_CASOS = 100;

function cargar(): MarcadorDatos | null {
  const f = path.join(process.cwd(), "public", "datos", "verificacion.json");
  if (!existsSync(f)) return null;
  return (JSON.parse(readFileSync(f, "utf8")) as { marcador?: MarcadorDatos }).marcador ?? null;
}

export default function Marcador() {
  const m = cargar();
  if (!m) return null;
  if (m.casos < MIN_CASOS)
    return (
      <p>
        <b>Cuánto acierta, cada día.</b> Desde el 25 de octubre de 2026 se guarda lo previsto para 35 aeropuertos y al
        día siguiente se compara con lo que observaron (METAR). El marcador aparecerá aquí cuando haya datos suficientes
        ({m.casos} de {MIN_CASOS} casos).
      </p>
    );
  const n = m.niebla;
  return (
    <>
      <p>
        Lo previsto el día anterior frente a lo observado en {m.aeropuertos} aeropuertos (METAR), del {m.desde.slice(8)}
        /{m.desde.slice(5, 7)} al {m.hasta.slice(8)}/{m.hasta.slice(5, 7)}: {m.casos} casos. Para que el número diga
        algo, se compara con «mañana igual que hoy».
      </p>
      <dl className="marcador-aciertos">
        <div>
          <dt>Nieblas al amanecer</dt>
          <dd>
            <b>
              {n.detectadas} de {n.observadas}
            </b>{" "}
            avisadas (probabilidad ≥ {Math.round(n.umbral * 100)} %); de {n.avisos} avisos, {n.avisos_acertados} con
            niebla
          </dd>
        </div>
        <div>
          <dt>Atardecer tapado por nubes bajas o medias</dt>
          <dd>
            <b>{m.atardecer_cubierto.acierto ?? "–"} %</b> de aciertos (repetir el día anterior:{" "}
            {m.atardecer_cubierto.persistencia ?? "–"} %)
          </dd>
        </div>
        <div>
          <dt>Noche despejada (≥ 3 h)</dt>
          <dd>
            <b>{m.noche_despejada.acierto ?? "–"} %</b> de aciertos (repetir el día anterior:{" "}
            {m.noche_despejada.persistencia ?? "–"} %)
          </dd>
        </div>
      </dl>
      <p className="nota-pie">
        El METAR apenas informa de nubes altas: no sirve para comprobar el «lienzo» de cirros del atardecer, solo si
        algo lo tapa.
      </p>
    </>
  );
}
