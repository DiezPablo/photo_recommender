import type { Metadata, Viewport } from "next";
import Link from "next/link";
import SelectorTema from "@/components/SelectorTema";
import { IconoInfo, Logo } from "@/components/Iconos";
import { cargar } from "@/lib/datos";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Spots de paisaje · Sierra de Madrid", template: "%s · Spots de paisaje" },
  description:
    "¿Merece la pena salir a fotografiar? Nota diaria de amanecer, atardecer, noche estrellada y niebla para spots de paisaje de la Sierra de Madrid, con el porqué.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f5f2ec" },
    { media: "(prefers-color-scheme: dark)", color: "#0f1217" },
  ],
};

// Aplica el tema guardado antes de pintar, para no ver un destello blanco en modo noche
const scriptTema = `try{var t=localStorage.getItem("tema");if(t)document.documentElement.dataset.tema=t}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const { informe } = cargar();
  const generado = informe ? new Date(informe.generado) : null;
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: scriptTema }} />
      </head>
      <body>
        <header className="cabecera">
          <div className="cabecera-in">
            <Link href="/" className="marca">
              <Logo />
              <span>
                <b>Spots de paisaje</b>
                <small>Sierra de Madrid · ¿merece la pena salir?</small>
              </span>
            </Link>
            <nav>
              <Link href="/acerca" aria-label="Cómo se puntúa" title="Cómo se puntúa">
                <IconoInfo size={18} /> <span className="solo-ancho">Cómo se puntúa</span>
              </Link>
              <SelectorTema />
            </nav>
          </div>
        </header>
        {children}
        <footer className="pie">
          <div>
            <span>
              Previsión:{" "}
              <a href="https://open-meteo.com/" rel="noopener">Open-Meteo</a> (CC BY 4.0) · Mapa: ©{" "}
              <a href="https://www.openstreetmap.org/copyright" rel="noopener">colaboradores de OpenStreetMap</a> · Fotos:{" "}
              <a href="https://commons.wikimedia.org/" rel="noopener">Wikimedia Commons</a> (autor y licencia en cada una) ·
              Contaminación lumínica:{" "}
              <a href="https://djlorenz.github.io/astronomy/lp/" rel="noopener">atlas de D. Lorenz 2025</a>
            </span>
            {generado && (
              <span>
                Datos generados el{" "}
                {generado.toLocaleString("es-ES", { timeZone: "Europe/Madrid", dateStyle: "long", timeStyle: "short" })}
                . Uso personal, sin fines comerciales.
              </span>
            )}
          </div>
        </footer>
      </body>
    </html>
  );
}
