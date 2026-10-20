# Spots de paisaje — contexto para Claude Code

Web personal (uso no comercial) para un fotógrafo aficionado en Madrid: para cada spot de paisaje y
cielo nocturno, nota diaria 0-10 de amanecer, atardecer, noche/Vía Láctea y niebla, con desglose
explicable. Todo gratuito y **sin IA/LLM por decisión del usuario**. El encargo original está en
`ENCARGO.md`; las decisiones y problemas, en `registro.md` (añade ahí lo nuevo).

## Piezas
- Pipeline Python (raíz): `descubrir_spots.py` (Commons + OSM → `public/datos/spots.geojson`),
  `condiciones.py` (Open-Meteo + `astro.py` + `contaminacion.py` + `puntuacion.py` → `public/datos/informe.json`),
  `comun.py` (ids de spot, JSON sin NaN), `notificar.py` (Telegram, opcional y desacoplado),
  `validar.py` (validación histórica: ERA5 + fotos de Commons + METAR; workflow `validar.yml`, artefacto `validacion`).
  Antes de cambiar pesos de `puntuacion.py`, mira el informe de validación y no ajustes más allá del ruido.
- Web Next.js 16 (App Router) en `src/`: páginas estáticas generadas en el build leyendo `public/datos`.
  `src/lib/datos.ts` solo servidor (usa `fs`); los componentes de cliente importan de `src/lib/modelo.ts`.
  Rutas: `/` (= `/dia/0/todos`), `/dia/[d]/[tipo]`, `/spot/[id]`, `/acerca`. Filtros de día y tipo son
  enlaces (funcionan sin JS); distancia y mapa (Leaflet, import dinámico) necesitan JS.
- Workflows: `datos.yml` (cada 3 h y al cambiar el código de notas), `descubrir.yml` (mensual y al cambiar
  el código de descubrimiento), `pruebas.yml` (pytest + typecheck + build + Playwright).
  `datos` y `descubrir` comparten grupo de concurrencia y hacen commit de `public/datos` a `main`;
  Vercel redespliega con cada commit.

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
- No hacer commit de `public/datos` a mano si Actions está publicando (conflictos): `git pull` primero.
