import type { Metadata, Viewport } from "next";
import { Archivo, IBM_Plex_Mono } from "next/font/google";
import Link from "next/link";
import SelectorTema from "@/ui/SelectorTema";
import RegistroSw from "@/features/offline/RegistroSw";
import { Logo } from "@/ui/Iconos";
import { cargar } from "@/features/spots/datos";
import "./globals.css";

// Tipografías autoalojadas en el build (sin peticiones a Google desde el navegador)
// Archivo (grotesca con eje de anchura: las cifras van estrechas) y Plex Mono para datos y rótulos.
const ui = Archivo({ subsets: ["latin"], variable: "--f-ui", display: "swap", axes: ["wdth"] });
const mono = IBM_Plex_Mono({ subsets: ["latin"], variable: "--f-mono", display: "swap", weight: ["400", "500"] });

export const metadata: Metadata = {
  title: { default: "Rasante · previsión para fotografía de paisaje", template: "%s · Rasante" },
  description:
    "¿Merece la pena salir a fotografiar? Nota diaria de amanecer, atardecer, noche estrellada, niebla y luna para spots de paisaje de toda España, con el porqué.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f2f1ed" },
    { media: "(prefers-color-scheme: dark)", color: "#0e0f11" },
  ],
};

// Aplica el tema guardado antes de pintar (sin destello blanco en modo noche) y atiende los botones de
// tema desde el primer momento, sin esperar a que cargue React (en el campo la cobertura es mala).
const scriptTema = `(function(){var d=document.documentElement;try{var t=localStorage.getItem("tema");if(t)d.dataset.tema=t}catch(e){}
document.addEventListener("click",function(e){var b=e.target&&e.target.closest&&e.target.closest("[data-tema-boton]");if(!b)return;
var t=b.getAttribute("data-tema-boton");d.dataset.tema=t;try{localStorage.setItem("tema",t)}catch(e){}
window.dispatchEvent(new CustomEvent("tema",{detail:t}))})})()`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const { informe } = cargar();
  const generado = informe ? new Date(informe.generado) : null;
  return (
    <html lang="es" suppressHydrationWarning className={`${ui.variable} ${mono.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: scriptTema }} />
      </head>
      <body>
        <header className="cabecera">
          <div className="cabecera-in">
            <Link href="/" className="marca" aria-label="Rasante, inicio">
              <Logo />
              <b>Rasante</b>
              <small className="solo-ancho">Previsión para fotografía de paisaje · España</small>
            </Link>
            <nav>
              <Link href="/">Spots</Link>
              <Link href="/rutas">Rutas</Link>
              <Link href="/calendario">Calendario</Link>
              <Link href="/acerca" className="solo-ancho">
                Método
              </Link>
              <SelectorTema />
            </nav>
          </div>
        </header>
        {children}
        <footer className="pie">
          <div>
            <span>
              <b>Rasante</b> · <Link href="/acerca">Método</Link> · <Link href="/alertas">Avisos en tu calendario</Link>{" "}
              · Previsión:{" "}
              <a href="https://open-meteo.com/" rel="noopener">
                Open-Meteo
              </a>{" "}
              (CC BY 4.0) · Mapa: ©{" "}
              <a href="https://www.openstreetmap.org/copyright" rel="noopener">
                colaboradores de OpenStreetMap
              </a>{" "}
              · Fotos:{" "}
              <a href="https://commons.wikimedia.org/" rel="noopener">
                Wikimedia Commons
              </a>{" "}
              (autor y licencia en cada una) · Contaminación lumínica:{" "}
              <a href="https://djlorenz.github.io/astronomy/lp/" rel="noopener">
                atlas de D. Lorenz 2025
              </a>{" "}
              · Rutas: OpenStreetMap,{" "}
              <a href="https://misendafedme.es" rel="noopener">
                FEDME
              </a>{" "}
              (CC BY 4.0) y Caminos Naturales (MAPA)
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
        <RegistroSw />
      </body>
    </html>
  );
}
