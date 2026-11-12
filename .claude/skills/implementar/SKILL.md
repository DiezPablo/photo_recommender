---
name: implementar
description: Implementa una spec de docs/specs/ de principio a fin - rama, plan, código, pruebas con verificador, revisión con revisor, cierre en backlog y decisiones.
argument-hint: "<número de spec>"
model: inherit  # usa el modelo de la sesión (Sonnet por defecto)
disable-model-invocation: true
---
Implementa la spec `docs/specs/$ARGUMENTS-*.md`. Empieza en una sesión limpia (si no lo es, pide a Pablo `/clear`).

1. Lee la spec y nada más de `docs/`. Si algo es ambiguo, pregunta antes de escribir código.
2. `git pull` y rama `spec/$ARGUMENTS-<slug>`.
3. Plan breve (lista de ficheros y pasos). Si toca más de ~10 ficheros o el pipeline y la web a la vez, enseña el
   plan y espera el visto bueno.
4. Implementa. Usa Explore para buscar en el código en vez de leer ficheros enteros. Tests nuevos para la lógica
   nueva (pytest sin red con fixtures; Playwright para lo visible).
5. Pide al subagente `verificador` que ejecute `make check` (y E2E si hay cambios visibles). Corrige y repite.
6. Pide al subagente `revisor` que revise la spec $ARGUMENTS. Corrige lo que marque como importante.
7. Cierre:
   - Marca la spec como `Estado: hecha` y su línea del backlog como hecha.
   - Si tomaste una decisión que alguien necesitará saber dentro de 3 meses, crea `docs/decisiones/NNNN-slug.md`.
   - Commit en español, push y PR con `gh pr create` (cuerpo: criterios de aceptación con su estado).
8. Dile a Pablo en 3 líneas qué ha cambiado y qué mirar en la web.
