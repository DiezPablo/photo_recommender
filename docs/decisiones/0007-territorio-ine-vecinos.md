# 0007 — Comunidad por código INE y descarte de países vecinos
Fecha: 2026-10-24 · Estado: vigente
Contexto: el geojson simplificado traía otra numeración (Asturias salía como «Ceuta») y metía spots de Portugal.
Decisión: la comunidad sale siempre de `rasante.comun.territorio.ccaa_de` (código INE de provincia); se
descartan puntos dentro de `recursos/vecinos.geojson` (Natural Earth, 200 m de margen; el mar se mantiene).
Consecuencias: todo dato nuevo con lugar (incluida la fauna migrada) pasa por estas dos funciones.
