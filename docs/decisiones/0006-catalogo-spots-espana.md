# 0006 — Catálogo nacional de spots: Wikidata + OSM, popularidad con Commons
Fecha: 2026-10-24 · Estado: vigente
Contexto: hace falta cubrir toda España con lugares de paisaje reales, gratis.
Decisión: candidatos de Wikidata (con P18) y OSM, fusionados (<400 m o mismo QID), popularidad por fotos de
Commons a 500 m con corrección por cielo urbano; 12 por provincia + el resto por nota hasta ~1500. Corre en
Actions (`descubrir.yml`, mensual) con caché persistente y corte por tiempo, porque Commons da 429 desde el
contenedor. Fotos de Google descartadas (de pago y no se pueden guardar).
Consecuencias: el catálogo es el activo (visión); su formato de caché (`CacheJson`) no se cambia.
