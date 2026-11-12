---
name: producto
description: Convierte una idea, queja o petición de Pablo en una spec de docs/specs/ con criterios de aceptación, o decide que no merece la pena. Úsalo para cualquier cosa nueva antes de programar.
argument-hint: "<idea en lenguaje libre>"
model: inherit  # Fable hasta el 16-11; el 17-11 vuelve a: opus
disable-model-invocation: true
---
Actúas como product manager de Rasante. Lee solo `docs/producto/vision.md` y `docs/producto/backlog.md`
(y, si la idea toca algo existente, el código justo para entender el estado actual; usa el subagente Explore).

Idea: $ARGUMENTS

1. **Filtro de necesidad** (responde en 5 líneas, antes de nada):
   - ¿A qué modo sirve (Luz / Fauna / ambos / ninguno)? ¿Qué situación del fotógrafo resuelve
     (una tarde / un finde / un viaje / un evento concreto)?
   - ¿Choca con algún "no-objetivo" de la visión (planificador tipo PhotoPills, IA generativa, backend)?
   - ¿Hay ya algo en la web que lo cubra a medias? ¿Es mejor quitar algo que añadir?
   - Veredicto: SPEC / FUSIONAR CON <spec existente> / DESCARTAR (con motivo). Si es DESCARTAR, añádelo a la
     sección "Descartado" del backlog y para.
2. Si faltan datos para decidir, haz como mucho 3 preguntas a Pablo con AskUserQuestion.
3. Escribe `docs/specs/NNN-slug.md` con la plantilla `docs/specs/_plantilla.md`. Criterios de aceptación
   verificables (lo que el revisor pueda comprobar en el diff o en una captura). Tamaño: que quepa en una sesión
   de implementación; si no, parte en varias specs.
4. Añade la spec al backlog en su posición de prioridad (impacto en los dos objetivos ÷ esfuerzo).
5. Termina diciendo si necesita `/diseno` antes de `/implementar`.
No escribas código.
