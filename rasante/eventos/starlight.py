"""Reservas y Destinos Turísticos Starlight (Fundación Starlight): cielos certificados.

La fundación publica los nombres, no los límites: `recursos/starlight.csv` lleva una zona aproximada (centro y
radio, varios círculos en Sierra Morena) o la provincia entera (Soria). La web lo presenta como aproximado.
Incluye las 22 Reservas y los Destinos con límites claros (islas, parques); faltan otros Destinos municipales.
"""

from __future__ import annotations

import csv

from rasante.comun.territorio import RECURSOS

CSV = RECURSOS / "starlight.csv"
FUENTE = "https://fundacionstarlight.org/contenido/84-mapa-reserva-y-destino-turistico-starlight.html"


def cargar() -> list[dict]:
    zonas = []
    with open(CSV, encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if fila["tipo"] not in ("reserva", "destino"):
                raise ValueError(f"{fila['id']}: tipo desconocido {fila['tipo']}")
            if not fila["provincia"] and not (fila["lat"] and fila["lon"] and fila["radio_km"]):
                raise ValueError(f"{fila['id']}: falta zona (lat, lon, radio) o provincia")
            zonas.append(
                {
                    "id": fila["id"],
                    "nombre": fila["nombre"],
                    "tipo": fila["tipo"],
                    "lat": float(fila["lat"]) if fila["lat"] else None,
                    "lon": float(fila["lon"]) if fila["lon"] else None,
                    "radio_km": float(fila["radio_km"]) if fila["radio_km"] else None,
                    "provincia": fila["provincia"] or None,
                }
            )
    return zonas
