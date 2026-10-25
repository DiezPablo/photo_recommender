// Los doce meses como enlaces (funciona sin JavaScript), para los dos calendarios.
import Link from "next/link";
import { type Ambito, MESES, rutaCalendario } from "@/features/eventos/modelo";

export default function NavMeses({ mes, mesHoy, ambito }: { mes: number; mesHoy: number; ambito: Ambito }) {
  return (
    <nav className="meses" aria-label="Meses">
      {MESES.map((m, i) => (
        <Link
          key={m}
          href={rutaCalendario(ambito, i)}
          aria-current={i === mes ? "page" : undefined}
          className={i === mesHoy ? "hoy" : undefined}
        >
          {m.slice(0, 3)}
        </Link>
      ))}
    </nav>
  );
}

/** Pestañas entre el calendario del paisaje y el de la fauna. */
export function PestanasCalendario({ ambito, mes }: { ambito: Ambito; mes?: number }) {
  return (
    <nav className="pestanas" aria-label="Calendarios">
      <Link href={rutaCalendario("paisaje", mes)} aria-current={ambito === "paisaje" ? "page" : undefined}>
        Paisaje y cielo
      </Link>
      <Link href={rutaCalendario("fauna", mes)} aria-current={ambito === "fauna" ? "page" : undefined}>
        Fauna
      </Link>
    </nav>
  );
}
