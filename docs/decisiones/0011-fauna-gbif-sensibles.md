# 0011 — Fauna con GBIF/OSM y sin ubicaciones exactas de especies sensibles
Fecha: 2026-10-25 · Estado: vigente
Contexto: hay que decir dónde ver fauna sin poner en riesgo especies amenazadas.
Decisión: observatorios de OSM + facetas de GBIF (no se descargan registros); meses normalizados por la
clase para quitar el sesgo de primavera; formas domésticas fuera (*Canis lupus familiaris*). Lince, oso,
lobo… solo por zonas (ya llegan generalizadas); fuera especies muy sensibles a la molestia (urogallo).
Consecuencias: la fauna migrada desde safari_recommender hereda estas reglas (ver spec 001).
