// Pestañas de la sección de fauna: lugares (observatorios), especies y calendario.
import Link from "next/link";

const PESTANAS = [
  { href: "/fauna", texto: "Lugares" },
  { href: "/fauna/especies", texto: "Especies" },
  { href: "/fauna/calendario", texto: "Calendario de fauna" },
] as const;

export default function PestanasFauna({ actual }: { actual: (typeof PESTANAS)[number]["href"] }) {
  return (
    <nav className="pestanas" aria-label="Fauna">
      {PESTANAS.map((p) => (
        <Link key={p.href} href={p.href} aria-current={p.href === actual ? "page" : undefined}>
          {p.texto}
        </Link>
      ))}
    </nav>
  );
}
