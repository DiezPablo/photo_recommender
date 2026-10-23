// El mejor plan del día elegido: foto del spot (o un cielo dibujado), nota grande y por qué.
import Link from "next/link";
import { NOMBRE_MOMENTO } from "@/lib/modelo";
import Anillo from "./Anillo";
import { IconoMomento, IconoRuta } from "./Iconos";
import type { FilaRanking } from "./tipos";

export default function Destacado({ f, foto, dia }: { f: FilaRanking; foto: string | null; dia: string }) {
  return (
    <article className={`destacado cielo-${f.momento}${foto ? " con-foto" : ""}`} aria-label="Mejor plan">
      {foto && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={foto} alt="" className="destacado-foto" fetchPriority="high" />
      )}
      <div className="destacado-in">
        <p className="antetitulo">Mejor plan · {dia}</p>
        <div className="destacado-fila">
          <Anillo nota={f.nota} tam={76} grosor={6} etiqueta={false} />
          <div style={{ minWidth: 0 }}>
            <h2><Link href={`/spot/${f.id}`}>{f.nombre}</Link></h2>
            <p className="destacado-meta">
              <IconoMomento momento={f.momento} size={15} /> {NOMBRE_MOMENTO[f.momento]} · {f.hora}
              {f.provincia ? ` · ${f.provincia}` : ""}
            </p>
          </div>
        </div>
        {f.motivos.length > 0 && <p className="destacado-porque">{f.motivos.join(" · ")}</p>}
        <div className="acciones">
          <Link className="boton primario" href={`/spot/${f.id}`}>Ver el plan</Link>
          <a className="boton translucido" href={`https://www.google.com/maps/dir/?api=1&destination=${f.lat},${f.lon}`}
            target="_blank" rel="noopener"><IconoRuta size={15} /> Cómo llegar</a>
        </div>
      </div>
    </article>
  );
}
