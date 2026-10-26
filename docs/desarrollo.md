# Desarrollo

## Entorno

```bash
make instalar
```

Crea `.venv` con el paquete en modo editable y sus herramientas (`pip install -e ".[dev]"`) e instala las
dependencias de la web (`npm ci`). Requisitos: Python 3.12+ y Node 20+.

## Órdenes

| `make` | Equivale a | Para qué |
|---|---|---|
| `make check` | `make check-python check-web` | Todo lo que comprueba la CI salvo el build y Playwright |
| `make check-python` | `ruff check`, `ruff format --check`, `pytest` | Pipeline |
| `make check-web` | `npm run check` (tsc, ESLint, Prettier) | Web |
| `make formato` | `ruff format`, `ruff check --fix`, `prettier --write` | Arreglar estilo |
| `make test` | `pytest` | Tests del pipeline (sin red) |
| `make web` | `npm run build && npm start` | Web en http://localhost:3000 con los datos publicados |
| `make e2e` | `npx playwright test` | Pruebas de la web en móvil y escritorio (capturas en `capturas/`) |
| `make e2e-produccion` | `BASE_URL=https://photo-recommender.vercel.app npx playwright test` | Las mismas pruebas contra producción |
| `make datos` | `npm run datos` | Solo descargar los datos publicados a `public/datos/` |
| `make prevision` | `python -m rasante prevision --mis-spots mis_spots.csv` | Previsión local en `public/datos/informe.json` |

Para construir con datos locales (generados con `python -m rasante …` en `public/datos/`):
`SIN_DESCARGA=1 npm run build`. Sin esa variable, el prebuild descarga los publicados a `datos/*.gz` (fuera de
`public/`), que el servidor lee antes que los locales (`src/lib/datos.ts`).

## Convenciones

- **Idioma**: código, comentarios, mensajes y textos de la web en español.
- **Python**: 3.12, ruff (configuración en `pyproject.toml`, líneas de 120). Cada paquete de `rasante/`
  tiene una responsabilidad; los `cli.py` solo leen argumentos y coordinan.
- **Web**: TypeScript estricto, ESLint (configuración de Next) y Prettier. Código por funcionalidad en
  `src/features/`; lo que lee ficheros con `fs` importa `server-only`; el estado del navegador se lee con
  los hooks de `src/lib/almacen.ts` (no con `setState` dentro de efectos).
- **Datos publicados**: JSON sin NaN (`rasante.comun.ficheros.escribir_json`, `allow_nan=False`).
- **Secretos**: solo por variables de entorno (`.env`, ver `.env.example`); nunca en código ni commits.
- **APIs**: caché en `cache/`, `Retry-After` y `maxlag` en Commons, User-Agent descriptivo
  (`rasante.comun.red`). Desde el contenedor de desarrollo Commons limita mucho: el descubrimiento real
  corre en Actions.
- **Territorio**: comunidad autónoma siempre con `rasante.comun.territorio.ccaa_de` (código INE de
  provincia); los puntos en países vecinos se descartan con `Provincias`.
- **Commits**: pequeños y explicativos. Haz `git pull` antes de `push`: Actions hace commits de
  `public/datos/version.json`.
- **Decisiones**: lo que se decide o se descubre, en [`decisiones.md`](decisiones.md).

## Pruebas

- **Pipeline** (`tests/`): sin red. Las respuestas reales de Open-Meteo y Commons están grabadas en
  `tests/fixtures`; la astronomía se contrasta con USNO y astropy. `tests/conftest.py` sirve la grabación de
  Open-Meteo y fija la contaminación lumínica. Hay un test que importa todos los módulos (detecta imports
  rotos dentro de funciones).
- **Web** (`e2e/`): Playwright en móvil y escritorio, sin errores de consola ni peticiones fallidas;
  incluye uso sin JavaScript, temas, «cerca de mí», rutas y GPX.
- En el contenedor de Claude Code la salida va por proxy: Playwright sirve la web en la IP de la máquina
  (no en `localhost`) para que Chromium cargue teselas y fotos (ver `playwright.config.ts`), y Python
  necesita `REQUESTS_CA_BUNDLE=/root/.ccr/ca-bundle.crt` para las APIs.
