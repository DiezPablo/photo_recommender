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
| Fauna: observatorios y especies emblemáticas (GBIF) | ¿Dónde y cuándo veo el lince, el oso, las grullas? | `/fauna`, `/fauna/especies` |
| Dron sí/no por spot (ENAIRE + AEMA) | ¿Puedo volar el dron aquí? | ficha de spot (`dron.json`) |
| Mareas y oleaje en la costa (Open-Meteo Marine) | ¿Bajamar al atardecer? ¿Mar en calma? | ficha de spot (`informe.json`, `mar`) |

## En pausa (25-10-2026): revisión de producto de mejoras gratuitas

El usuario pidió una revisión de mejoras gratuitas; se hicieron las dos primeras (dron y mareas) y se pausó
para empezar los safaris. Orden acordado para retomar, de más a menos prioridad:

1. **«Visto hace poco cerca de aquí»**: iNaturalist (`/v1/observations/species_counts`, sin clave) en spots,
   observatorios y especies; eBird «notables» con clave gratuita por variable de entorno.
2. **Imagen para compartir** cada spot con la nota del día (`next/og`).
3. **Eclipse total del 2-8-2027**: página con la franja, duración por spot, altura del sol y nubosidad ERA5.
4. **Panorama con picos** (estilo PeakFinder): horizonte del DEM + picos de OSM + trayectoria de sol y luna.
5. Notas nuevas: arcoíris, cascadas con agua (lluvia 3-7 días), nieve recién caída/cencellada, tormentas.
6. Avisos oficiales (Meteoalarm/AEMET CAP), riesgo de incendio (EFFIS), puertos cerrados (DGT DATEX II),
   accesos regulados (CSV curado), «foto sin andar» (distancia al aparcamiento), favoritos con `.ics` propio,
   RSS, fotos de Commons por mes, teselas sin conexión de una ruta, relieve iluminado a una hora,
   floraciones medidas con iNaturalist, GTFS para llegar sin coche.

## Siguiente

1. **Spots y rutas cruzados en el mapa**: rutas que pasan por un spot (no solo las que acaban en él).
2. **Planificador con mapa** y orden por distancia en coche entre los puntos de cada día.
3. **Más eventos** (orquídeas, brezo, luciérnagas, tormentas, cencelladas) y Destinos Starlight municipales.
4. **Hora local en Canarias en todo el pipeline** (hoy el informe va en hora peninsular).
5. **Marcador ampliado** en cuanto haya meses de historial: por comunidad y por plazo (1, 2 y 3 días).
