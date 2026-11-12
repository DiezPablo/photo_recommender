# Backlog

Una línea por spec, en orden de prioridad. Estado: `[ ]` pendiente · `[~]` en curso · `[x]` hecha.
Lo crea y reordena `/producto`; lo marca como hecho `/implementar`.

## Ahora
- [x] 001 — Auditoría y plan de consolidación (`docs/specs/001-consolidacion.md`)
- [ ] 002 — Auditoría de licencias y cobertura de la base de datos (curador-datos)
- [ ] 003 — Esquema único de "lugar": `lugares.json` y validador (`docs/specs/003-esquema-lugar.md`)
- [ ] 005 — Retirada de safaris (código, workflows, páginas, datos) con redirecciones (001 §3)
- [ ] 006 — Cuadrícula de fauna (GBIF, estacionalidad, backtest) en `rasante/fauna` (001 §5)
- [ ] 007 — Lugares de fauna unificados: observatorios OSM + eBird + espacios protegidos (requiere 003)
- [ ] 008 — Recientes, rarezas y actividad (eBird, iNaturalist) con secretos y licencias
- [ ] 012 — Consulta común "cuándo / dónde / qué" en la URL y portada que la lanza. CA: una URL reproduce cualquier resultado; funciona sin JS; pestañas Luz/Fauna
- [ ] 004 — Sistema de diseño y rediseño de portada y ficha de lugar (sobre las seis pantallas de `modos.md`)
- [ ] 009 — Carta de fauna en `/fauna` (cuadrícula de 10 km)
- [ ] 010 — Ficha de lugar única (bloques Luz y Fauna según `modos`) y ficha de especie
- [ ] 011 — Situaciones "una tarde / este finde", hides, rarezas y normas
- [ ] 013 — Idoneidad del lugar por momento y resultados fuera de previsión. CA: `luz.idoneidad` (amanecer, atardecer, noche) con desglose en `lugares.json`; ranking para cualquier fecha = climatología × idoneidad, marcado como "lo habitual"
- [ ] 014 — Eventos con varios lugares. CA: la berrea lista ≥ 8 lugares de ≥ 4 comunidades con franja y fiabilidad; `fenomenos.ts` fusionado en `eventos_naturaleza.csv`; `eventos` relleno en `lugares.json`
- [ ] 015 — "¿Dónde verlo?" en eventos de cielo. CA: la ficha de Perseidas enlaza a resultados de noche para su fecha y la zona elegida, con luna y horas de Vía Láctea
- [ ] 016 — Plan de varios días sobre el esquema nuevo. CA: `/viaje` Asturias-octubre da por día luz + fauna + eventos en temporada; sin bloques podados

## Después
- [ ] Poda de "información justa": decidir sobre los candidatos de 001 §6 (alineaciones, mareas, rutas, logística, dron…)

## Descartado
