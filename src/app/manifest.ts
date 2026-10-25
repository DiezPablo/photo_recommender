import type { MetadataRoute } from "next";

// Instalable como app: en el campo se abre desde la pantalla de inicio y funciona sin cobertura con lo guardado.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Rasante · fotografía de paisaje y senderismo",
    short_name: "Rasante",
    description: "Previsión para fotografía de paisaje, rutas y calendario de temporadas en España.",
    lang: "es",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#f3f2ee",
    theme_color: "#141413",
    icons: [
      { src: "/iconos/icono-192.png", sizes: "192x192", type: "image/png" },
      { src: "/iconos/icono-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
