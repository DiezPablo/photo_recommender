# 0009 — Respeto de límites de APIs gratuitas
Fecha: 2026-10-23 · Estado: vigente
Contexto: Open-Meteo (10 000 llamadas/día), Commons (429), Overpass (cortes), GBIF e iNaturalist limitan.
Decisión: rejillas compartidas y 10 variables por punto en Open-Meteo, 2 previsiones al día; User-Agent
descriptivo, `Retry-After`, `maxlag`, espejos de Overpass, ≤ 1 pet/s a iNaturalist; extracto PBF para
consultas nacionales; trabajos largos incrementales con `--minutos` y caché entre ejecuciones de Actions.
Consecuencias: nuevos workflows deben sumar su consumo al de `datos.yml` y no solaparse en la misma API.
