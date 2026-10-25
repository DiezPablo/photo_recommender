"use client";
// Navegación del móvil: barra inferior con las secciones (a mano del pulgar). En pantallas anchas no se ve.
import Link from "next/link";
import { usePathname } from "next/navigation";
import { IconoCalendario, IconoCamara, IconoMochila, IconoPajaro, IconoRuta } from "@/ui/Iconos";

const SECCIONES = [
  { href: "/", texto: "Spots", Icono: IconoCamara, activa: (p: string) => p === "/" || /^\/(dia|spot)\//.test(p) },
  { href: "/rutas", texto: "Rutas", Icono: IconoRuta, activa: (p: string) => /^\/rutas?(\/|$)/.test(p) },
  { href: "/fauna", texto: "Fauna", Icono: IconoPajaro, activa: (p: string) => p.startsWith("/fauna") },
  { href: "/viaje", texto: "Viaje", Icono: IconoMochila, activa: (p: string) => p.startsWith("/viaje") },
  {
    href: "/calendario",
    texto: "Calendario",
    Icono: IconoCalendario,
    activa: (p: string) => /^\/(calendario|evento|alertas)/.test(p) && !p.startsWith("/fauna"),
  },
];

export default function BarraInferior() {
  const ruta = usePathname() ?? "/";
  return (
    <nav className="barra-inferior" aria-label="Secciones">
      {SECCIONES.map(({ href, texto, Icono, activa }) => (
        <Link key={href} href={href} aria-current={activa(ruta) ? "page" : undefined}>
          <Icono size={22} />
          <span>{texto}</span>
        </Link>
      ))}
    </nav>
  );
}
