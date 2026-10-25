"""Climatología fotográfica: qué cabe esperar cada mes en cada zona (para planificar más allá de la previsión).

Con el reanálisis ERA5 (archivo de Open-Meteo, 2021-2025) en una rejilla de 0,5° sobre España se calculan,
con los mismos modelos de nota que la previsión, la frecuencia de amaneceres y atardeceres buenos, de noches
despejadas y de madrugadas con niebla en cada mes.

- `rejilla`: puntos de la rejilla (tierra y franja costera).
- `era5`: descarga de cada punto (una vez, con presupuesto de llamadas) y resumen diario compacto.
- `agregar`: notas diarias (con el camino del sol por los puntos vecinos) y probabilidades por mes.
- `cli`: `python -m rasante clima`.
"""
