"""Rasante: previsión para fotografía de paisaje y nocturna, y rutas de senderismo, en toda España.

Subpaquetes:
  comun       utilidades compartidas (caché, red, JSON, identificadores, territorio)
  cielo       astronomía (sol, luna, Vía Láctea) y contaminación lumínica
  terreno     modelo digital del terreno: altura y horizonte
  notas       modelos de puntuación 0-10 (luz, noche, niebla, luna)
  prevision   Open-Meteo + notas → informe.json
  spots       descubrimiento de spots en toda España → spots.geojson
  rutas       rutas de senderismo (OSM, FEDME, Caminos Naturales) → rutas.json
  validacion  validación histórica de las notas
  avisos      resumen diario por Telegram (opcional)

Uso: python -m rasante <orden> [opciones]   (python -m rasante --help)
"""

__version__ = "2.0.0"
