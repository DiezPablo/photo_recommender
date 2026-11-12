# 0002 — Presupuesto de Vercel: 1 GB de build y 30 días de despliegues
Fecha: 2026-10-26 · Estado: vigente
Contexto: las fichas prerenderizadas pasaron de 800 MB y cada despliegue ocupaba ~650 MB (Hobby guarda 30 días).
Decisión: se prerenderiza solo lo que se visita mucho (top 60 spots del día); el resto de fichas es ISR con
sus `.gz` en la función (`outputFileTracingIncludes`, solo los que usa cada ruta). En `public/datos` solo lo
que pide el navegador. Retención de despliegues al mínimo en el panel.
Consecuencias: cualquier funcionalidad nueva declara su coste en MB por despliegue y nº de despliegues/día.
