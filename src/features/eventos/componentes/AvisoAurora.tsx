// Aviso de aurora (tormenta geomagnética fuerte prevista por NOAA): solo aparece cuando hay algo que ver.
import { type Aurora, fechaLarga, TEXTO_AURORA } from "@/features/eventos/modelo";

export default function AvisoAurora({ aurora: a }: { aurora: Aurora | null }) {
  if (!a?.noche) return null;
  return (
    <aside className="aviso-aurora" role="note">
      <b>{TEXTO_AURORA[a.nivel]}</b> la noche del {fechaLarga(a.noche, false)} (índice Kp previsto{" "}
      {a.kp_max.toLocaleString("es-ES")}). Busca un sitio oscuro con el horizonte norte despejado y haz fotos de varios
      segundos: la cámara la capta mucho antes que el ojo.{" "}
      <a href={a.fuente} rel="noopener">
        Pronóstico de NOAA
      </a>
    </aside>
  );
}
