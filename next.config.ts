import type { NextConfig } from "next";

const DATOS_VIAJE = [
  "./public/datos/informe.json",
  "./public/datos/spots.geojson",
  "./public/datos/clima.json",
  "./public/datos/eventos.json",
  "./public/datos/alineaciones.json",
  "./public/datos/fauna.json",
  "./public/datos/especies.json",
  "./public/datos/rutas.json",
];

const config: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Las fotos vienen de upload.wikimedia.org ya en miniatura de 640 px: no hace falta optimizarlas
  images: { unoptimized: true },
  // Las fichas de ruta se generan al visitarlas (ISR) y leen rutas.json en la función del servidor
  // (y las de spot fuera del top, que leen el informe y los spots); las dos muestran los eventos cercanos
  outputFileTracingIncludes: {
    // el planificador se genera en cada petición: solo los datos que usa (con «*.json» se llevaba también los de
    // safaris, ~8 MB más en cada función)
    "/viaje": DATOS_VIAJE,
    "/viaje/calendario.ics": DATOS_VIAJE,
    "/ruta/[id]": [
      "./public/datos/rutas.json",
      "./public/datos/eventos.json",
      "./public/datos/informe.json",
      "./public/datos/spots.geojson",
      "./public/datos/logistica.json",
      "./public/datos/fauna.json",
    ],
    "/safaris/[id]": [
      "./public/datos/safaris.json",
      "./public/datos/safaris_mundo.json",
      "./public/datos/safaris_recientes.json",
    ],
    "/spot/[id]": [
      "./public/datos/informe.json",
      "./public/datos/spots.geojson",
      "./public/datos/eventos.json",
      "./public/datos/rutas.json",
      "./public/datos/clima.json",
      "./public/datos/alineaciones.json",
      "./public/datos/logistica.json",
      "./public/datos/fauna.json",
      "./public/datos/dron.json",
    ],
  },
};

export default config;
