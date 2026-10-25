# Operación

Todo se ejecuta en GitHub Actions. No hace falta ningún secreto salvo para el aviso opcional por Telegram.

## Workflows

| Workflow | Cuándo | Qué hace | Duración |
|---|---|---|---|
| [`datos.yml`](../.github/workflows/datos.yml) | 03:47 y 12:47 UTC, y al cambiar `rasante/{prevision,notas,cielo,terreno,comun}` o `mis_spots.csv` | Descarga los spots publicados, calcula la previsión y el calendario y publica `informe.json` y `eventos.json`. A mediodía, aviso por Telegram | ~40 min |
| [`descubrir.yml`](../.github/workflows/descubrir.yml) | Día 1 de cada mes (02:41 UTC) y al cambiar `rasante/spots` o el territorio | Descubre ~1500 spots, recalcula la previsión y publica `spots.geojson`, `spots.csv` e `informe.json` | 4-5 h |
| [`rutas.yml`](../.github/workflows/rutas.yml) | Día 8 de cada mes (04:23 UTC) y al cambiar `rasante/rutas` | Descarga el extracto de OSM de España, lee FEDME y Caminos Naturales, publica `rutas.json` | ~25 min |
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
| Una ficha de spot o ruta da 404 | El id ya no existe (los spots se recalculan cada mes) | Normal; el ranking enlaza siempre a ids vigentes |

## Despliegue (Vercel)

Configuración en [`vercel.json`](../vercel.json) (Next.js, `npm ci`, `npm run build`). El *prebuild* descarga
los datos de la release (`scripts/descargar-datos.mjs`). [`.vercelignore`](../.vercelignore) deja fuera el
pipeline, los tests y la documentación.
