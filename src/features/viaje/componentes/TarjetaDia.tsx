import Link from "next/link";
import Cifra from "@/ui/Cifra";
import { deCada } from "@/features/clima/modelo";
import { fechaCorta, textoAlineacion } from "@/features/eventos/modelo";
import { duracion } from "@/features/rutas/modelo";
import type { DiaPlan, Propuesta } from "@/features/viaje/plan";

const TITULO: Record<Propuesta["momento"], string> = {
  amanecer: "Amanecer",
  atardecer: "Atardecer",
  noche: "Noche y Vía Láctea",
  luna: "Luna sobre el paisaje",
};

/** «despejada 1 de cada 3 noches», «bueno casi nunca». */
function habitual(p: Propuesta, pct: number) {
  const cada = deCada(pct);
  const noche = p.momento === "noche" || p.momento === "luna";
  const cuantos = cada.startsWith("1 de cada") ? `${cada} ${noche ? "noches" : "días"}` : cada;
  return `${noche ? "despejada" : "bueno"} ${cuantos}`;
}

function Momento({ p }: { p?: Propuesta }) {
  if (!p) return null;
  return (
    <div className={`plan-momento plan-${p.momento === "luna" ? "noche" : p.momento}`}>
      <p className="rotulo">
        {TITULO[p.momento]}
        {p.hora && ` · ${p.momento === "noche" ? "desde las " : ""}${p.hora}`}
      </p>
      <Link href={`/spot/${p.spot.id}`} className="plan-spot">
        {p.spot.nombre}
      </Link>
      <small>
        {p.spot.provincia && `${p.spot.provincia} · `}
        {p.nota !== undefined ? (
          <>
            nota prevista <Cifra nota={p.nota} />
            {p.nota < 5 && " · día flojo en toda la zona"}
          </>
        ) : p.pct !== undefined ? (
          <>lo habitual: {habitual(p, p.pct)}</>
        ) : null}
      </small>
      {p.ruta && (
        <small className="plan-ruta">
          Subiendo por <Link href={`/ruta/${p.ruta.id}`}>{p.ruta.nombre}</Link>: sal a las <b>{p.ruta.salida}</b> (
          {duracion(p.ruta.horas)} de subida)
        </small>
      )}
    </div>
  );
}

export default function TarjetaDia({ d }: { d: DiaPlan }) {
  const fecha = new Date(`${d.fecha}T12:00:00Z`).toLocaleDateString("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  });
  return (
    <article className="tarjeta-dia-viaje">
      <header>
        <h2>{fecha}</h2>
        <span className={`etiqueta-fuente ${d.previsto ? "previsto" : "habitual"}`}>
          {d.previsto ? "Con previsión" : "Lo habitual (sin previsión aún)"}
        </span>
        <span className="luna-dia">
          Luna al {Math.round(d.luna * 100)} %
          {d.kmRecta > 0 && ` · ${d.kmRecta.toLocaleString("es-ES")} km entre paradas en línea recta`}
        </span>
      </header>
      <div className="plan-momentos">
        <Momento p={d.amanecer} />
        <Momento p={d.atardecer} />
        <Momento p={d.noche} />
      </div>
      {d.ruta && (
        <p className="plan-ruta-dia">
          <b>Ruta:</b> <Link href={`/ruta/${d.ruta.id}`}>{d.ruta.nombre}</Link> · {d.ruta.km.toLocaleString("es-ES")}{" "}
          km, +{d.ruta.subida} m, {duracion(d.ruta.horas)}, {d.ruta.dificultad} · cerca de {d.ruta.cerca}
        </p>
      )}
      {(d.fauna || d.faunaEventos.length > 0) && (
        <p className="plan-ruta-dia">
          <b>Fauna:</b>{" "}
          {d.faunaEventos.map((e, i) => (
            <span key={e.id}>
              {i > 0 && ", "}
              <Link href={`/evento/${e.id}`}>{e.nombre}</Link>
            </span>
          ))}
          {d.faunaEventos.length > 0 && d.fauna && " · "}
          {d.fauna && (
            <>
              <Link href={`/fauna/${d.fauna.id}`}>{d.fauna.nombre}</Link> (a {d.fauna.km} km:{" "}
              {d.fauna.especies.join(", ")})
            </>
          )}
        </p>
      )}
      {(d.naturaleza.length > 0 || d.alineaciones.length > 0 || d.cielo.length > 0) && (
        <ul className="plan-extras">
          {d.cielo.map((c) => (
            <li key={c}>{c}</li>
          ))}
          {d.alineaciones.map(({ spot, a }) => (
            <li key={`${spot.id}-${a.cuerpo}-${a.azimut}`}>
              <Link href={`/spot/${spot.id}`}>{spot.nombre}</Link>, {a.hora}: {textoAlineacion(a).toLowerCase()}
            </li>
          ))}
          {d.naturaleza.map((e) => (
            <li key={e.id}>
              <Link href={`/evento/${e.id}`}>{e.nombre}</Link> (hasta el {fechaCorta(e.hasta)})
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
