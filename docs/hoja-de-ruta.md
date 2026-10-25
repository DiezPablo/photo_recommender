# Hoja de ruta: planificador de viajes

Objetivo del usuario: que Rasante sea el sitio para **planificar un viaje de fotografía, senderismo y
naturaleza con todo dentro**. Siempre gratuito, con datos abiertos y sin IA. El análisis frente a otras
webs y apps (Alpenglow, Sunsethue, PhotoPills, The Photographer's Ephemeris, Locationscout, PhotoHound,
Wikiloc, Komoot, AllTrails, Astrospheric, Clear Outside) está en `decisiones.md` (25-10-2026).

## Hecho

| Pieza | Qué responde | Dónde |
|---|---|---|
| Previsión por spot (5 días) con desglose | ¿Merece la pena salir, a dónde y por qué? | `/`, `/spot/[id]` |
| Rutas (8500) con filtros, perfil y GPX | ¿Qué ruta hago, de cuánta distancia y desnivel? | `/rutas`, `/ruta/[id]` |
| «Sal a las…» | ¿A qué hora salgo para tener arriba la luz buena? | fichas de ruta y spot |
| Calendario de eventos | ¿Qué hay que ver en esta época, y dónde? | `/calendario`, `/evento/[id]` |
| Avisos `.ics` por zona | Que los buenos momentos lleguen solos, gratis y sin cuenta | `/alertas` |
| Web instalable y sin conexión | Usarla en el monte sin cobertura | botón «Guardar» en las fichas |
| Auroras (Kp) y cielos Starlight | ¿Hay tormenta geomagnética? ¿Es un cielo certificado? | portada, calendario, fichas |
| Climatología ERA5 por mes | ¿Qué semana voy, más allá de la previsión? | fichas, calendario, planificador (cuando `clima.yml` complete la rejilla) |
| Alineaciones de sol y luna | ¿Cuándo sale el sol o la luna llena por ese pico? | fichas de spot, calendario |
| Planificador de viaje | Zona y fechas → qué hacer cada día | `/viaje` |
| Logística de OSM | ¿Dónde aparco, hay agua, refugio, camping? | fichas de spot y ruta |
| «Nubes ahora» (satélite) | ¿Salgo ya? | todos los mapas |
| Marcador de aciertos (METAR) | ¿Cuánto me puedo fiar? | `/acerca` (con ≥ 100 casos) |

## Siguiente

1. **Spots y rutas cruzados en el mapa**: rutas que pasan por un spot (no solo las que acaban en él).
2. **Planificador con mapa** y orden por distancia en coche entre los puntos de cada día.
3. **Más eventos** (orquídeas, brezo, luciérnagas, tormentas, cencelladas) y Destinos Starlight municipales.
4. **Hora local en Canarias en todo el pipeline** (hoy el informe va en hora peninsular).
5. **Marcador ampliado** en cuanto haya meses de historial: por comunidad y por plazo (1, 2 y 3 días).
