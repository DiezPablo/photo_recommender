# Rasante — contexto para Claude Code

Web personal (uso no comercial) de previsión para fotografía de paisaje y nocturna en toda España: para cada
spot, nota diaria 0-10 de amanecer, atardecer, noche/Vía Láctea, niebla y luna, con desglose explicable; y
rutas de senderismo. Todo gratuito y **sin IA/LLM por decisión del usuario**. El encargo original está en
`docs/encargo.md`; las decisiones y problemas, en `docs/decisiones.md` (añade ahí lo nuevo). Arquitectura,
modelos, operación y desarrollo, en `docs/`.

## Piezas
- Pipeline Python: paquete `rasante/` (`pyproject.toml`), una orden por subpaquete con
  `python -m rasante {prevision,spots,rutas,eventos,alineaciones,clima,fauna,especies,dron,safaris,logistica,verificar,validar,avisos}`:
  - `comun` (caché `CacheJson`, sesión HTTP, `escribir_json` sin NaN, `id_spot`, `territorio`),
    `cielo` (astro, contaminación lumínica), `terreno` (DEM, horizonte), `notas` (modelos con desglose),
    `prevision` (Open-Meteo, y Marine para mareas y oleaje en la costa → `public/datos/informe.json`), `spots` (Commons + Wikidata + OSM →
    `spots.geojson`), `rutas` (PBF de OSM + FEDME/Caminos Naturales del IGN → `rutas.json`),
    `eventos` (luna, meteoros, Vía Láctea, eclipses, auroras, Starlight, naturaleza de
    `recursos/eventos_naturaleza.csv` → `eventos.json`; alineaciones → `alineaciones.json`), `clima` (ERA5 por
    mes → `clima.json`, workflow `clima.yml`, varios días la primera vez), `fauna` (observatorios de OSM + GBIF →
    `fauna.json`; especies de `recursos/especies.csv` + GBIF → `especies.json`), `safaris` (65 destacados de `recursos/safaris.csv` + iNaturalist + ERA5 + OSM → `safaris.json`;
    `--mundo`: todos los parques con fauna de Wikidata cribados con GBIF + NASA + OurAirports + OSM →
    `safaris_mundo.json` e índice; workflow `safaris.yml`; `--recientes` a diario → `safaris_recientes.json`), `dron` (zonas UAS de ENAIRE + espacios protegidos de la AEMA → `dron.json`), `validacion` (ERA5 + Commons + METAR), `avisos` (Telegram, opcional), `recursos` (geojson de referencia).
  - Antes de cambiar pesos de `rasante/notas/`, mira el informe de validación (artefacto `validacion`) y no
    ajustes más allá del ruido.
- Web Next.js 16 (App Router) en `src/`: `app/` (rutas finas), `features/{spots,rutas,eventos,clima,fauna,safaris,dron,viaje,alertas,offline}` (componentes, modelo,
  `datos.ts` solo servidor con `server-only`), `ui/` (incl. `mapa/useMapaBase.ts` para Leaflet), `lib/`
  (`almacen.ts`: estado del navegador con `useSyncExternalStore`; `ubicacion.ts`), `estilos/` (CSS por áreas).
  Páginas generadas en el build, salvo `/viaje` (dinámica: depende de zona y fechas), `/spot/[id]` (fuera del top 60
  del día) y `/ruta/[id]`, que se generan al visitarlas (ISR) para no pasar el límite de 1 GB de Vercel; sus JSON van en la función con
  `outputFileTracingIncludes` (`next.config.ts`).
- Workflows: `datos.yml` (2 veces al día), `safaris.yml` (semanal), `safaris_mundo.yml` (diario, incremental), `descubrir.yml` (mensual, ~1500 spots, 4-5 h), `rutas.yml` (mensual),
  `validar.yml`, `pruebas.yml` (ruff + pytest; tsc + ESLint + Prettier + build + Playwright).
  Los datos (`informe.json`, `spots.geojson`, `spots.csv`, `rutas.json`, `eventos.json`) **no van en git**: se suben a la release
  `datos` (`.github/scripts/publicar_release.sh`) y solo se hace commit de `public/datos/version.json`, que
  dispara el redespliegue de Vercel (solo si algún fichero cambió). `npm run build` los descarga antes (prebuild) a
  `datos/*.gz`, fuera de `public/`: el servidor los lee con `src/lib/datos.ts` (`leerDatos`) y solo `fauna.json` y
  `safaris_indice.json` (los que pide el navegador) van a `public/datos`. `SIN_DESCARGA=1` usa los de `public/datos`
  (salida local del pipeline). Vercel guarda 30 días de despliegues: cuidado con su tamaño y con cuántos se crean.

## Probar
- `make check` (ruff, pytest sin red con respuestas reales en `tests/fixtures`, tsc, ESLint, Prettier).
- `npm run build && npx playwright test` (móvil y escritorio, capturas en `capturas/`);
  `make e2e-produccion` prueba https://photo-recommender.vercel.app.
- En el contenedor de Claude Code la salida va por proxy: Playwright sirve la web en la IP de la máquina
  (no en localhost), ver `playwright.config.ts`; Python necesita `REQUESTS_CA_BUNDLE=/root/.ccr/ca-bundle.crt`.

## Convenciones
- Python 3.12, código, comentarios y textos de la web en español. ruff y Prettier deciden el formato.
- Secretos solo por variables de entorno (`.env`, ver `.env.example`); nunca en código ni commits.
- JSON publicados sin NaN (`rasante.comun.ficheros.escribir_json`).
- Bbox con coordenadas negativas: `--bbox=-4.30,40.60,-3.55,41.10` (con `=`).
- Respetar límites de las APIs: caché en `cache/` (no cambiar el formato de `CacheJson`), `Retry-After` y
  `maxlag` en Commons, User-Agent descriptivo, espejos de Overpass. Desde el contenedor Commons limita mucho
  (429): el descubrimiento real corre en GitHub Actions.
- `git pull` antes de hacer push: Actions hace commits de `public/datos/version.json`.
- Comunidad autónoma siempre con `rasante.comun.territorio.ccaa_de` (código INE de provincia); los puntos en
  países vecinos se descartan con `rasante/recursos/vecinos.geojson`.
