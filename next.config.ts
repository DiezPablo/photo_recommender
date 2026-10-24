import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Las fotos vienen de upload.wikimedia.org ya en miniatura de 640 px: no hace falta optimizarlas
  images: { unoptimized: true },
  // Las fichas de ruta se generan al visitarlas (ISR) y leen rutas.json en la función del servidor
  outputFileTracingIncludes: { "/ruta/[id]": ["./public/datos/rutas.json"] },
};

export default config;
