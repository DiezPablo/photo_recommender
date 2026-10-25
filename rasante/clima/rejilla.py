"""Rejilla de 0,5° sobre España: puntos en tierra o a menos de ~30 km de la costa (el camino del sol en los
atardeceres de costa pasa por el mar)."""

from __future__ import annotations

import json
from functools import cache

from shapely.geometry import Point, shape
from shapely.ops import unary_union

from rasante.comun.territorio import PROVINCIAS

PASO = 0.5
MARGEN_GRADOS = 0.3
CAJAS = [(35.5, 44.0, -9.5, 4.5), (27.5, 29.5, -18.5, -13.0)]  # península y Baleares; Canarias


def id_punto(lat: float, lon: float) -> str:
    return f"{lat:.2f}_{lon:.2f}"


@cache
def puntos() -> list[tuple[float, float]]:
    espana = unary_union([shape(f["geometry"]) for f in json.loads(PROVINCIAS.read_text())["features"]])
    zona = espana.buffer(MARGEN_GRADOS)
    lista = []
    for la0, la1, lo0, lo1 in CAJAS:
        la = la0
        while la <= la1 + 1e-9:
            lo = lo0
            while lo <= lo1 + 1e-9:
                if zona.contains(Point(lo, la)):
                    lista.append((round(la, 2), round(lo, 2)))
                lo += PASO
            la += PASO
    return lista


def vecino(lat: float, lon: float) -> tuple[float, float]:
    """El punto de la rejilla más cercano (para asignar un spot a su celda)."""
    return min(puntos(), key=lambda p: (p[0] - lat) ** 2 + ((p[1] - lon) * 0.77) ** 2)
