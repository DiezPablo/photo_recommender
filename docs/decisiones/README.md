# Decisiones

Un fichero por decisión: `NNNN-slug.md`, máximo ~20 líneas. Sustituye al antiguo `decisiones.md`
(archivado en `docs/archivo/`, no se lee salvo que se pida).

Plantilla:

```
# NNNN — Título
Fecha: AAAA-MM-DD · Estado: vigente | sustituida por NNNN
Contexto: por qué hubo que decidir (2-3 líneas).
Decisión: qué se decidió.
Consecuencias: qué implica y qué queda descartado.
```

Índice (una línea por decisión):

- [0001](0001-sin-backend-release-datos.md) — Sin backend: Actions calcula, la release `datos` guarda, Vercel sirve
- [0002](0002-limites-vercel.md) — Presupuesto de Vercel: 1 GB de build y 30 días de despliegues
- [0003](0003-notas-aditivas-explicables.md) — Notas aditivas con desglose
- [0004](0004-validacion-antes-de-pesos.md) — Pesos validados empíricamente; no ajustar dentro del ruido
- [0005](0005-astronomia-propia.md) — Astronomía propia (astral + Meeus), sin skyfield
- [0006](0006-catalogo-spots-espana.md) — Catálogo nacional de spots: Wikidata + OSM, popularidad con Commons
- [0007](0007-territorio-ine-vecinos.md) — Comunidad por código INE y descarte de países vecinos
- [0008](0008-horizonte-dem.md) — Orientación = horizonte real del terreno
- [0009](0009-limites-apis.md) — Respeto de límites de APIs gratuitas
- [0010](0010-rutas-fuentes-abiertas.md) — Rutas solo de fuentes abiertas (OSM, FEDME/IGN, Caminos Naturales)
- [0011](0011-fauna-gbif-sensibles.md) — Fauna con GBIF/OSM y sin ubicaciones exactas de especies sensibles
- [0012](0012-paisaje-y-fauna-separados.md) — Dos ámbitos: paisaje y cielo / fauna
- [0013](0013-no-planificador-de-toma.md) — No competir con PhotoPills; safaris fuera de España fuera
- [0014](0014-web-sin-js-y-offline.md) — Funciona sin JavaScript y sin cobertura
