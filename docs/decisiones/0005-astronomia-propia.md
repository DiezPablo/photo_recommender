# 0005 — Astronomía propia (astral + Meeus), sin skyfield
Fecha: 2026-10-19 · Estado: vigente
Contexto: skyfield descarga efemérides de JPL en cada ejecución.
Decisión: astral para sol y luna, Meeus para iluminación lunar y centro galáctico; contrastado con USNO y
astropy en tests (≤ 3-4 min, < 0,5°). En la web, `src/lib/sol.ts` (NOAA), ±1 min frente al pipeline.
Consecuencias: precisión de "dónde y cuándo ir", no de planificador de toma (ver 0013).
