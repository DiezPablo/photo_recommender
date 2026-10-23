// Nota 0-10 como cifra estrecha teñida con la escala de luz.
import { calificacion } from "@/lib/modelo";

export default function Cifra({ nota, className = "" }: { nota: number; className?: string }) {
  const cal = calificacion(nota);
  return (
    <span className={`cifra ${cal.clase} ${className}`} title={`${cal.texto}: ${nota.toFixed(1)} sobre 10`}>
      {nota.toFixed(1)}
    </span>
  );
}
