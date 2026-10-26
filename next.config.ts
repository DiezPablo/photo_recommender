import type { NextConfig } from "next";

const DATOS_VIAJE = [
  "./datos/informe.json.gz",
  "./datos/spots.geojson.gz",
  "./datos/clima.json.gz",
  "./datos/eventos.json.gz",
  "./datos/alineaciones.json.gz",
  "./datos/fauna.json.gz",
  "./datos/especies.json.gz",
  "./datos/rutas.json.gz",
];

const config: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Las fotos vienen de upload.wikimedia.org ya en miniatura de 640 px: no hace falta optimizarlas
  images: { unoptimized: true },
  // Las fichas de ruta se generan al visitarlas (ISR) y leen rutas.json en la función del servidor
  // (y las de spot fuera del top, que leen el informe y los spots); las dos muestran los eventos cercanos
  outputFileTracingIncludes: {
    // el planificador se genera en cada petición: solo los datos que usa, comprimidos (datos/*.gz)
    "/viaje": DATOS_VIAJE,
    "/viaje/calendario.ics": DATOS_VIAJE,
    "/ruta/[id]": [
      "./datos/rutas.json.gz",
      "./datos/eventos.json.gz",
      "./datos/informe.json.gz",
      "./datos/spots.geojson.gz",
      "./datos/logistica.json.gz",
      "./datos/fauna.json.gz",
    ],
    "/fauna/[id]": [
      "./datos/fauna.json.gz",
      "./datos/eventos.json.gz",
      "./datos/rutas.json.gz",
      "./datos/especies.json.gz",
    ],
    "/safaris/[id]": ["./datos/safaris.json.gz", "./datos/safaris_mundo.json.gz", "./datos/safaris_recientes.json.gz"],
    "/spot/[id]": [
      "./datos/informe.json.gz",
      "./datos/spots.geojson.gz",
      "./datos/eventos.json.gz",
      "./datos/rutas.json.gz",
      "./datos/clima.json.gz",
      "./datos/alineaciones.json.gz",
      "./datos/logistica.json.gz",
      "./datos/fauna.json.gz",
      "./datos/dron.json.gz",
    ],
  },
};

export default config;
