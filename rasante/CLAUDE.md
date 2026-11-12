# rasante/ — pipeline de datos (Python)

Una orden por subpaquete: `python -m rasante <orden>` (`--help` para verlas).

- `comun`: caché `CacheJson` (no cambies su formato), sesión HTTP, `escribir_json` sin NaN, `id_spot`,
  `territorio` (CCAA siempre con `territorio.ccaa_de`, por código INE de provincia).
- `cielo` (astro, contaminación lumínica), `terreno` (DEM, horizonte), `notas` (modelos con desglose).
- `prevision`: Open-Meteo (+ Marine en costa) → `informe.json`. `spots`: Commons + Wikidata + OSM →
  `spots.geojson`. `rutas`: PBF de OSM + FEDME/IGN → `rutas.json`. `eventos`: luna, meteoros, Vía Láctea,
  eclipses, auroras, Starlight y `recursos/eventos_naturaleza.csv` → `eventos.json`; alineaciones.
- `clima` (ERA5 por mes), `fauna` (observatorios OSM + GBIF; `recursos/especies.csv`), `dron` (ENAIRE + AEMA),
  `logistica`, `verificacion`, `validacion` (ERA5 + Commons + METAR), `avisos` (Telegram, opcional).
- `safaris`: en retirada (spec 006), no le añadas nada.

Reglas:
- Antes de cambiar pesos de `notas/`, mira el informe de validación (artefacto `validacion`); no ajustes más
  allá del ruido.
- Respeta los límites de las APIs: caché en `cache/`, `Retry-After` y `maxlag` en Commons, User-Agent
  descriptivo, espejos de Overpass. El descubrimiento real corre en GitHub Actions (desde el contenedor, 429).
- Bbox con negativos: `--bbox=-4.30,40.60,-3.55,41.10` (con `=`). Puntos en países vecinos se descartan con
  `recursos/vecinos.geojson`.
- Tests: pytest sin red con respuestas reales grabadas en `tests/fixtures` (no las leas enteras).

Publicación: los datos no van en git. Se suben a la release `datos` (`.github/scripts/publicar_release.sh`) y
solo se hace commit de `public/datos/version.json`, que redespliega Vercel si algo cambió.
