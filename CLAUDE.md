# Rasante — contexto para Claude Code

Web de referencia para fotógrafos de naturaleza en España: **dónde ir**. Dos modos:
- **Luz y cielo**: amanecer, atardecer, hora azul, Vía Láctea y eventos astronómicos → qué spots y cuándo.
- **Fauna**: una tarde, un finde o un viaje, con o sin evento (berrea, grullas, celo…) → dónde y qué esperar.

Rasante indica el lugar y el momento; no es un planificador de toma (no competimos con PhotoPills).
Detalle en `docs/producto/vision.md`. Qué toca hacer: `docs/producto/backlog.md`. Cómo trabajamos:
`docs/flujo-de-trabajo.md` (léelo solo si la tarea es sobre el propio proceso).

## Reglas fijas
- Sin IA generativa ni LLM en el producto. Sin backend: GitHub Actions calcula, la release `datos` almacena,
  Vercel sirve (Next.js estático + ISR).
- Todo cambio de producto parte de una spec en `docs/specs/`. Sin spec, pregunta antes de programar.
- Decisiones nuevas: un fichero corto en `docs/decisiones/` (plantilla en su README). No leas
  `docs/archivo/` salvo que se pida.
- Código, comentarios y textos en español. Python 3.12 (ruff), TypeScript (ESLint + Prettier).
- Secretos solo por variables de entorno. JSON publicados sin NaN (`rasante.comun.ficheros.escribir_json`).
- `git pull` antes de push: Actions hace commits de `public/datos/version.json`.

## Piezas (detalle en `rasante/CLAUDE.md` y `src/CLAUDE.md`, se cargan al trabajar ahí)
- `rasante/`: pipeline Python, `python -m rasante <orden>`.
- `src/`: web Next.js 16 App Router (`app/` rutas finas, `features/<área>/`, `ui/`, `lib/`, `estilos/`).
- `.github/workflows/`: datos, descubrimiento, pruebas.

## Probar
- `make check` (ruff, pytest sin red, tsc, ESLint, Prettier). E2E: `npm run build && npx playwright test`.
- Delega la ejecución de pruebas en el subagente `verificador` para no llenar el contexto de logs.
- En el contenedor: Playwright sirve en la IP de la máquina; Python necesita
  `REQUESTS_CA_BUNDLE=/root/.ccr/ca-bundle.crt`. Commons/Overpass/GBIF limitan: el cálculo real va en Actions.
