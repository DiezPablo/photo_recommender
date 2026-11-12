# Flujo de trabajo con Claude Code

## Principio
El repositorio guarda todo lo importante; las conversaciones son desechables. Cada tarea va en una sesión
limpia que lee solo lo que necesita. Así se gastan pocos tokens y se puede cambiar de idea sin arrastrar
contexto viejo.

```
idea ──► /producto (Opus) ──► docs/specs/NNN.md ──► /diseno (Opus, si hay interfaz)
                                                         │
             /clear ◄── PR ◄── revisor (Sonnet) ◄── verificador (Haiku) ◄── /implementar NNN (Sonnet)
```

## Roles
| Rol | Dónde vive | Modelo | Por qué así |
|---|---|---|---|
| Producto: requisitos y "¿cubre una necesidad?" | skill `/producto` | Opus | Necesita juicio y hablar contigo; corre en la sesión principal |
| Diseño visual y UX | skill `/diseno` | Opus | Las decisiones visuales se pagan caras si salen mal |
| Implementación | skill `/implementar` | el de la sesión (Sonnet) | El grueso del trabajo; Sonnet sobra para seguir una spec clara |
| Pruebas | subagente `verificador` | Haiku | Ejecutar y resumir; los logs se quedan en su contexto, no en el tuyo |
| Revisión contra la spec | subagente `revisor` | Sonnet | Contexto limpio: no se "califica a sí mismo" |
| Calidad de la base de datos | subagente `curador-datos` | Sonnet | Analiza datos con scripts sin cargarlos en la conversación |
| Buscar en el código | subagente integrado `Explore` | (el suyo) | Lee extractos en vez de ficheros enteros |

Requisitos y "análisis de necesidad" van juntos en `/producto`: separarlos duplica lecturas sin mejorar el
resultado. Tampoco hay un "orquestador": tú decides el orden mirando el backlog.

## Reglas de ahorro
1. Una spec = una sesión. `/clear` al terminar. Nunca dos repos en la misma sesión.
2. Modelo por defecto Sonnet (`.claude/settings.json`). Opus solo en `/producto` y `/diseno`. Haiku para ejecutar.
3. `CLAUDE.md` corto; el detalle en `rasante/CLAUDE.md` y `src/CLAUDE.md`, que solo se cargan al trabajar ahí.
4. No se leen datos generados, fixtures ni el archivo (`permissions.deny`).
5. Decisiones en ficheros cortos, no en un registro que crece sin fin.
6. Peticiones pequeñas y concretas que apunten a una spec, en vez de "mejora la web".
7. `/compact` solo si una sesión se alarga; si se alarga mucho, la spec era demasiado grande.

## Cuándo usar Fable
Solo mientras esté incluido en el plan. Para tareas de alto apalancamiento y una sola pasada: auditorías de todo
el repo, arquitectura de datos, sistema de diseño, migraciones grandes. Nunca para tareas rutinarias.
