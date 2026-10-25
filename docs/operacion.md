# Operación

Todo se ejecuta en GitHub Actions. No hace falta ningún secreto salvo para el aviso opcional por Telegram.

## Workflows

| Workflow | Cuándo | Qué hace | Duración |
|---|---|---|---|
| [`datos.yml`](../.github/workflows/datos.yml) | 03:47 y 12:47 UTC, y al cambiar `rasante/{prevision,notas,cielo,terreno,comun,eventos,verificacion}` o `mis_spots.csv` | Previsión (`informe.json`), calendario (`eventos.json`), alineaciones (`alineaciones.json`), verificación con METAR (`verificacion.json`, con su historial) y avistamientos de 30 días en los parques de safari (`safaris_recientes.json`). A mediodía, aviso por Telegram. La verificación nunca bloquea la publicación | ~40 min |
| [`descubrir.yml`](../.github/workflows/descubrir.yml) | Día 1 de cada mes (02:41 UTC) y al cambiar `rasante/spots` o el territorio | Descubre ~1500 spots, recalcula la previsión y publica `spots.geojson`, `spots.csv` e `informe.json` | 4-5 h |
| [`rutas.yml`](../.github/workflows/rutas.yml) | Día 8 de cada mes (04:23 UTC) y al cambiar `rasante/rutas` o `rasante/logistica` | Extracto de OSM de España, FEDME y Caminos Naturales → `rutas.json`; con el mismo extracto, aparcamientos, agua, refugios y campings → `logistica.json`; observatorios de fauna (`fauna.json`), especies emblemáticas con GBIF (`especies.json`) y si se puede volar un dron en cada spot (`dron.json`) | ~30 min |
| [`safaris.yml`](../.github/workflows/safaris.yml) | Domingos (03:13 UTC) y al cambiar `rasante/safaris` | Catálogo curado (`safaris.json`) y todos los parques del mundo con fauna (`safaris_mundo.json`, `safaris_indice.json`): Wikidata, GBIF, NASA POWER, OurAirports y una tanda de OSM por ejecución (caché `safaris-v1-*`) | 2-5 h |
| [`clima.yml`](../.github/workflows/clima.yml) | 08:17 y 20:17 UTC, y al cambiar `rasante/clima` o `rasante/notas` | Climatología ERA5: descarga los puntos de la rejilla que quepan en ~4000 llamadas (caché `clima-v1-*`) y, con la rejilla completa, publica `clima.json`. La primera vez tarda varios días | ~1 h |
| [`validar.yml`](../.github/workflows/validar.yml) | A mano y al cambiar `rasante/notas` o `rasante/validacion` | Validación histórica; informe en el resumen y en el artefacto `validacion` | ~1-2 h |
| [`pruebas.yml`](../.github/workflows/pruebas.yml) | Cada push y pull request | ruff + pytest; tipos, ESLint, Prettier, build y Playwright | ~5 min |

GitHub ejecuta el cron en UTC y suele retrasarlo. Los que publican datos llaman a
[`publicar_release.sh`](../.github/scripts/publicar_release.sh): sube los ficheros (y su `.gz`) a la release
`datos`, actualiza `public/datos/version.json` y hace commit, que dispara el despliegue de Vercel.

## Lanzar a mano

*Actions → (workflow) → Run workflow*. Opciones:
- **Datos**: «Enviar aviso por Telegram» para probar el aviso.
- **Descubrir spots**: número de spots, mínimo por provincia y minutos máximos para Commons.

## Cachés

| Caché | Contenido | Dónde |
|---|---|---|
| `descubrir-*` | Respuestas de Commons, Wikidata y Overpass; teselas del DEM y del atlas | `actions/cache` (se guarda aunque el trabajo falle) |
| `rutas-*` | Teselas del DEM; respuestas del IGN (se borran cada mes) | `actions/cache` |
| `atlas-lp-2025` | Teselas del atlas de contaminación lumínica | `actions/cache` |
| `clima-v1-*` | Resumen diario por punto de la rejilla ERA5 (`cache/clima`) | `actions/cache` (se guarda aunque el trabajo falle) |

El formato de los ficheros de caché (`rasante.comun.cache.CacheJson`) no debe cambiar sin motivo: invalidaría
horas de peticiones a Commons.

## Aviso por Telegram (opcional)

1. Crea un bot con @BotFather y escríbele algo.
2. `TELEGRAM_TOKEN=… python -m rasante avisos --chat-id` para sacar tu chat.
3. Añade los secretos `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID` en *Settings → Secrets and variables → Actions*.

Sin ellos, el paso se salta sin error.

## Si algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| *Descubrir* agota el tiempo | Commons lento o con 429 | Nada: la caché se guarda y la siguiente ejecución continúa. Se puede bajar `minutos` |
| *Datos* falla con «no responde» | Open-Meteo caído o límite diario | Se reintenta en la siguiente ejecución; comprobar el estado de Open-Meteo |
| La web no muestra datos nuevos | Falló el commit de `version.json` o el despliegue | Ver el paso *Publicar* del workflow y los despliegues de Vercel |
| *Rutas* no descarga el extracto | Geofabrik caído | El workflow prueba también openstreetmap.fr |
| La climatología no aparece en la web | La rejilla aún no está completa | Ver el progreso («N/300») en el log de *Climatología*; se completa sola |
| El marcador de aciertos no aparece | Menos de 100 casos en el historial | Se llena solo en unos días |
| Una ficha de spot o ruta da 404 | El id ya no existe (los spots se recalculan cada mes) | Normal; el ranking enlaza siempre a ids vigentes |

## Despliegue (Vercel)

Configuración en [`vercel.json`](../vercel.json) (Next.js, `npm ci`, `npm run build`). El *prebuild* descarga
los datos de la release (`scripts/descargar-datos.mjs`). [`.vercelignore`](../.vercelignore) deja fuera el
pipeline, los tests y la documentación.
