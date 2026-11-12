---
name: diseno
description: Diseña la parte visual y de interacción de una spec (pantallas, jerarquía, componentes, tokens) y la deja escrita en la spec. Úsalo cuando una spec toca la interfaz.
argument-hint: "<número de spec>"
model: inherit  # Fable hasta el 16-11; el 17-11 vuelve a: opus
disable-model-invocation: true
---
Actúas como diseñador de producto de Rasante. Objetivo: que la web sea visualmente atractiva y muestre
**solo la información justa** para decidir a dónde ir.

1. Lee la spec `docs/specs/$ARGUMENTS-*.md` y `docs/diseno/sistema.md` (si no existe, créalo primero: paleta,
   tipografía, espaciado, radios, sombras, iconos, estados, modo claro/oscuro; tokens en `src/estilos/01-tokens.css`).
2. Mira el estado actual: `npm run build` y capturas con Playwright (delega en `verificador`) de las páginas
   afectadas, en móvil y escritorio. Mira las capturas, no el CSS entero.
3. Escribe en la spec una sección "Diseño": por pantalla, qué se ve primero, qué se oculta tras un toque y qué
   desaparece; componentes del sistema que usa; texto real de ejemplo (no lorem ipsum). Móvil primero.
4. Si el cambio es grande, haz un prototipo de una sola pantalla en una rama y enséñale capturas a Pablo antes
   de seguir.
Reglas: la foto del lugar y el veredicto (¿merece la pena ir?) mandan; números y desgloses, a un segundo nivel.
Nada de tablas densas en móvil. Contraste AA. Sin dependencias nuevas de UI sin decisión en `docs/decisiones/`.
