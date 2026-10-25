"""Cuánto acierta la previsión: lo previsto para ~35 aeropuertos frente a lo que observaron (METAR).

El color de un atardecer no se puede comprobar cada día sin fotos, pero sí sus ingredientes: la niebla al
amanecer (FG o visibilidad < 1 km), el cielo tapado por nubes bajas y medias al atardecer (BKN/OVC) y las
noches despejadas. El METAR apenas informa de nubes altas, así que no se verifica el «lienzo» de cirros.

- `aeropuertos`: estaciones y coordenadas.
- `previsto`: la previsión de Open-Meteo para los aeropuertos (una sola petición) con los mismos criterios.
- `observado`: METAR (Iowa Environmental Mesonet) por aeropuerto y día.
- `marcador`: historial (60 días) y aciertos de los últimos 30 con la previsión del día anterior.
"""
