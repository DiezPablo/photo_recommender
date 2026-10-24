# Spots de paisaje — contexto para Claude Code

Web personal (uso no comercial) para un fotógrafo aficionado en Madrid: para cada spot de paisaje y
cielo nocturno, nota diaria 0-10 de amanecer, atardecer, noche/Vía Láctea y niebla, con desglose
explicable. Todo gratuito y **sin IA/LLM por decisión del usuario**. El encargo original está en
`ENCARGO.md`; las decisiones y problemas, en `registro.md` (añade ahí lo nuevo).

## Piezas
- Pipeline Python (raíz): `descubrir_spots.py` (Commons + OSM → `public/datos/spots.geojson`),
  `condiciones.py` (Open-Meteo + `astro.py` + `contaminacion.py` + `puntuacion.py` → `public/datos/informe.json`),
  `comun.py` (ids de spot, JSON sin NaN), `notificar.py` (Telegram, opcional y desacoplado),
  `rutas.py` (rutas de senderismo: extracto PBF de OSM + FEDME/Caminos Naturales del IGN → `rutas.json`;
  workflow `rutas.yml`, mensual), `validar.py` (validación histórica: ERA5 + fotos de Commons + METAR; workflow `validar.yml`, artefacto `validacion`).
  Antes de cambiar pesos de `puntuacion.py`, mira el informe de validación y no ajustes más allá del ruido.
- Web Next.js 16 (App Router) en `src/`: páginas generadas en el build leyendo `public/datos`, salvo las
  fichas `/spot/[id]` (fuera del top del día) y `/ruta/[id]`, que se generan al visitarlas (ISR, caché hasta
  el siguiente despliegue) para no pasar el límite de 1 GB de ficheros estáticos de Vercel; los JSON que leen
  van en la función con `outputFileTracingIncludes` (`next.config.ts`).
  `src/lib/datos.ts` solo servidor (usa `fs`); los componentes de cliente importan de `src/lib/modelo.ts`.
  Rutas: `/` (= `/dia/0/todos`), `/dia/[d]/[tipo]`, `/spot/[id]`, `/acerca`, `/rutas`, `/rutas/[ccaa]`,
  `/ruta/[id]` (JSON estáticos: `/datos-rutas/indice` y `/datos-rutas/celda/[c]`, trazados por celdas de 1°). Filtros de día y tipo son
  enlaces (funcionan sin JS); distancia y mapa (Leaflet, import dinámico) necesitan JS.
- Workflows: `datos.yml` (2 veces al día y al cambiar el código de notas), `descubrir.yml` (mensual y al
  cambiar el código de descubrimiento; `descubrir_espana.py`, ~1500 spots de toda España, 4-5 h),
  `pruebas.yml` (pytest + typecheck + build + Playwright).
  Los datos (`informe.json`, `spots.geojson`, `spots.csv`, `rutas.json`) **no van en git**: se suben a la release `datos`
  (`.github/scripts/publicar_release.sh`) y solo se hace commit de `public/datos/version.json`, que
  dispara el redespliegue de Vercel. `npm run build` los descarga antes (prebuild; `SIN_DESCARGA=1` usa
  los locales).

## Probar
- `python -m pytest -q` (sin red: respuestas reales guardadas en `tests/fixtures`; astronomía
  contrastada con USNO y astropy).
- `npm run build && npx playwright test` (móvil y escritorio, capturas en `capturas/`).
  Con `BASE_URL=https://photo-recommender.vercel.app` prueba producción.
- En el contenedor de Claude Code la salida va por proxy: Playwright sirve la web en la IP de la
  máquina (no en localhost) para que Chromium cargue teselas y fotos; ver `playwright.config.ts`.

## Convenciones
- Python 3.12, código, comentarios y textos de la web en español.
- Secretos solo por variables de entorno (`.env`, ver `.env.example`); nunca en código ni commits.
- JSON publicados sin NaN (`comun.escribir_json` con `allow_nan=False`).
- Bbox con coordenadas negativas: `--bbox=-4.30,40.60,-3.55,41.10` (con `=`).
- Respetar límites de las APIs: caché en `cache/`, `Retry-After` y `maxlag` en Commons, User-Agent
  descriptivo, espejos de Overpass. Desde el contenedor de desarrollo Commons limita mucho (429):
  el descubrimiento real corre en GitHub Actions.
- `git pull` antes de hacer push: Actions hace commits de `public/datos/version.json`.
- Comunidad autónoma siempre con `comun.ccaa_de` (código INE de provincia); los spots en países vecinos
  se descartan con `datos_base/vecinos.geojson`.
