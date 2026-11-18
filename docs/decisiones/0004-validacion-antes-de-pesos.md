# 0004 — Pesos validados empíricamente; no ajustar dentro del ruido
Fecha: 2026-10-20 · Estado: vigente
Contexto: v2 de luz (AUC 0,60 con fotos de Commons + ERA5) y niebla (AUC 0,92 con METAR) se ajustaron con datos.
Decisión: los pesos solo cambian mirando el informe de validación (`validar.yml`) y no por diferencias del
orden del ruido (~0,01 de AUC). Lo no validable (noche, mar de nubes, mareas) se razona físicamente y no entra
como factor si no hay con qué validarlo (las mareas son informativas).
Consecuencias: cambios de `rasante/notas/` exigen validación; marcador METAR diario como seguimiento.
