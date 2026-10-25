# Hoja de ruta: planificador de viajes

Objetivo del usuario: que Rasante sea el sitio para **planificar un viaje de fotografía, senderismo y
naturaleza con todo dentro**. Siempre gratuito, con datos abiertos y sin IA.

## Hecho

| Pieza | Qué responde |
|---|---|
| Previsión por spot (5 días) | ¿Merece la pena salir mañana, y a dónde? |
| Rutas (8400) con filtros | ¿Qué ruta hago por aquí, de cuánta distancia y desnivel? |
| Calendario de eventos | ¿Qué hay que ver en esta época, y dónde? |
| Eventos cercanos en spots y rutas | ¿Qué merece la pena aquí en otra época? |

## Siguiente

1. **Plan de viaje por zona y fechas** (`/viaje`): elegir zona (comunidad, mapa o «cerca de mí») y fechas.
   - Dentro de los próximos 5 días: las notas reales de cada spot y día.
   - Más allá: lo que se puede esperar (eventos en marcha, luna, ventana de Vía Láctea, horas de sol) y la
     climatología (nubosidad media del mes con ERA5, que ya usa la validación).
   - Propuesta día a día: amanecer en un spot, ruta de mañana, atardecer y noche, con distancias en coche.
   - Se guarda en la URL (compartible) y se exporta a GPX/calendario (.ics).
2. **Spots y rutas cruzados**: rutas que pasan por un spot o cerca; spots en el recorrido de una ruta.
3. **Logística con datos abiertos**: refugios, áreas de autocaravana, aparcamientos y fuentes de OSM;
   restricciones y cupos de espacios protegidos donde haya datos.
4. **Ampliar el calendario**: más eventos (orquídeas, brezo, luciérnagas, tormentas, cencelladas) y
   alineaciones de sol y luna con elementos del relieve en cada spot (el horizonte ya se calcula).

Cada paso se publica cuando funciona solo, con pruebas en móvil y escritorio.
