// Lo primero de la portada: el mejor spot del día y filtro elegidos, con su foto si la hay.
import Link from "next/link";
import { NOMBRE_CORTO } from "@/lib/modelo";
import type { Foto } from "@/lib/modelo";
import Cifra from "./Cifra";
import type { FilaRanking } from "./tipos";

export default function Destacado({ f, foto, credito }: { f: FilaRanking; foto: string | null; credito: Foto | null }) {
  return (
    <article className="destacado" aria-label="Mejor plan">
      <div className="destacado-fila">
        <Cifra nota={f.nota} className="enorme" />
        <div className="destacado-txt">
          <p className="rotulo">{NOMBRE_CORTO[f.momento]} · {f.hora}{f.provincia ? ` · ${f.provincia}` : ""}</p>
          <h2><Link href={`/spot/${f.id}`}>{f.nombre}</Link></h2>
          {f.motivos.length > 0 && <p className="destacado-porque">{f.motivos.join(". ")}.</p>}
          <p className="enlaces">
            <Link href={`/spot/${f.id}`}>Ver el plan completo →</Link>
            <a href={`https://www.google.com/maps/dir/?api=1&destination=${f.lat},${f.lon}`} target="_blank" rel="noopener">
              Cómo llegar ↗
            </a>
          </p>
        </div>
      </div>
      {foto && credito && (
        <figure className="foto-tira">
          <Link href={`/spot/${f.id}`} tabIndex={-1}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={foto} alt={credito.titulo || f.nombre} fetchPriority="high" />
          </Link>
          <figcaption>
            Foto: <a href={credito.enlace} target="_blank" rel="noopener">{credito.autor}</a> · {credito.licencia || "Wikimedia Commons"}
          </figcaption>
        </figure>
      )}
    </article>
  );
}
