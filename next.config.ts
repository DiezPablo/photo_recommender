import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Las fotos vienen de upload.wikimedia.org ya en miniatura de 640 px: no hace falta optimizarlas
  images: { unoptimized: true },
  // Las fichas de ruta se generan al visitarlas (ISR) y leen rutas.json en la función del servidor
  // (y las de spot fuera del top, que leen el informe y los spots); las dos muestran los eventos cercanos
  outputFileTracingIncludes: {
    // el planificador se genera en cada petición con todos los datos
    "/viaje": ["./public/datos/*.json", "./public/datos/spots.geojson"],
    "/viaje/calendario.ics": ["./public/datos/*.json", "./public/datos/spots.geojson"],
    "/ruta/[id]": [
      "./public/datos/rutas.json",
      "./public/datos/eventos.json",
      "./public/datos/informe.json",
      "./public/datos/spots.geojson",
      "./public/datos/logistica.json",
    ],
    "/spot/[id]": [
      "./public/datos/informe.json",
      "./public/datos/spots.geojson",
      "./public/datos/eventos.json",
      "./public/datos/rutas.json",
      "./public/datos/clima.json",
      "./public/datos/alineaciones.json",
      "./public/datos/logistica.json",
    ],
  },
};

export default config;
