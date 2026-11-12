# src/ — web (Next.js 16, App Router)

- `app/`: rutas finas; la lógica va en `features/`.
- `features/<área>/`: componentes, modelo y `datos.ts` (solo servidor, con `server-only`). Áreas: spots, rutas,
  eventos, clima, fauna, dron, viaje, alertas, offline, logistica, verificacion; `safaris` en retirada (spec 006).
- `ui/`: componentes comunes; `ui/mapa/useMapaBase.ts` para Leaflet.
- `lib/`: `datos.ts` (`leerDatos`, lee `datos/*.gz`), `almacen.ts` (estado del navegador con
  `useSyncExternalStore`), `ubicacion.ts`.
- `estilos/`: CSS por áreas; tokens en `01-tokens.css`. Sistema de diseño en `docs/diseno/sistema.md`.

Datos: `npm run build` los descarga antes (prebuild) a `datos/*.gz`, fuera de `public/`. Solo lo que pide el
navegador va a `public/datos`. `SIN_DESCARGA=1` usa la salida local del pipeline.

Generación: casi todo en el build. `/viaje` es dinámica; `/spot/[id]` fuera del top 60 del día y `/ruta/[id]`
van por ISR con sus JSON incluidos en la función (`outputFileTracingIncludes` en `next.config.ts`) para no
pasar 1 GB en Vercel. Vercel guarda 30 días de despliegues: vigila su tamaño y cuántos se crean.

Pruebas visibles con Playwright (móvil y escritorio, capturas en `capturas/`); en el contenedor sirve en la IP
de la máquina (ver `playwright.config.ts`).
