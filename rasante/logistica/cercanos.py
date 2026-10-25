"""Los puntos útiles más cercanos a cada lugar, con un índice de celdas para no comparar todos con todos."""

from __future__ import annotations

import math
from collections import defaultdict

# tipo: (radio en km, cuántos como mucho)
RADIOS = {
    "aparcamiento": (1.5, 2),
    "fuente": (2.0, 2),
    "refugio": (6.0, 3),
    "autocaravanas": (15.0, 1),
    "camping": (15.0, 2),
}
CELDA = 0.1  # grados


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


class Indice:
    def __init__(self, puntos: list[dict]):
        self.celdas: dict[tuple[str, int, int], list[dict]] = defaultdict(list)
        for p in puntos:
            self.celdas[(p["tipo"], int(p["lat"] // CELDA), int(p["lon"] // CELDA))].append(p)

    def cerca(self, lat: float, lon: float) -> list[dict]:
        salida = []
        for tipo, (radio, n) in RADIOS.items():
            alcance = math.ceil(radio / (111 * CELDA * math.cos(math.radians(lat)))) + 1
            ci, cj = int(lat // CELDA), int(lon // CELDA)
            cand = []
            for i in range(ci - alcance, ci + alcance + 1):
                for j in range(cj - alcance, cj + alcance + 1):
                    for p in self.celdas.get((tipo, i, j), ()):
                        d = km((lat, lon), (p["lat"], p["lon"]))
                        if d <= radio:
                            cand.append((d, p))
            # sin repetir el mismo sitio mapeado dos veces (nodo y área a pocos metros)
            elegidos: list[tuple[float, dict]] = []
            for d, p in sorted(cand, key=lambda x: x[0]):
                if all(km((p["lat"], p["lon"]), (q["lat"], q["lon"])) > 0.08 for _, q in elegidos):
                    elegidos.append((d, p))
                if len(elegidos) == n:
                    break
            salida += [{**p, "km": round(d, 2)} for d, p in elegidos]
        return salida
