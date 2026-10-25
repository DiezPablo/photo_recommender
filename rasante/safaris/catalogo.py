"""Catálogo de parques de safari (recursos/safaris.csv): escrito a mano con fuentes contrastadas.

Las tasas solo se ponen cuando son conocidas y con su año; si no, la web remite a la web oficial del parque.
"""

from __future__ import annotations

import csv
from pathlib import Path

from rasante.comun.territorio import RECURSOS

CSV = RECURSOS / "safaris.csv"
CONTINENTES = {"África", "Asia", "América", "Oceanía", "Europa"}
TIPOS = {
    "4x4",
    "a pie",
    "en coche propio",
    "globo",
    "barco",
    "canoa",
    "primates",
    "nocturno",
    "buceo",
    "autobús",
    "avioneta",
    "vehículo de tundra",
}


def _lista(v: str) -> list[str]:
    return [x for x in v.split("|") if x]


def cargar(ruta: Path = CSV) -> list[dict]:
    parques, vistos = [], set()
    with open(ruta, encoding="utf-8") as f:
        for n, fila in enumerate(csv.DictReader(f), start=2):
            if None in fila or any(v is None for v in fila.values()):
                raise ValueError(f"línea {n}: campos de más o de menos (¿una coma sin comillas?)")
            for c in ("id", "nombre", "pais", "continente", "lat", "lon", "radio_km", "tipos", "meses", "consejo"):
                if not fila[c]:
                    raise ValueError(f"línea {n}: falta {c}")
            if fila["id"] in vistos:
                raise ValueError(f"{fila['id']}: id repetido")
            vistos.add(fila["id"])
            if fila["continente"] not in CONTINENTES:
                raise ValueError(f"{fila['id']}: continente desconocido {fila['continente']}")
            tipos = _lista(fila["tipos"])
            if desconocidos := set(tipos) - TIPOS:
                raise ValueError(f"{fila['id']}: tipos de safari desconocidos {desconocidos}")
            meses = [int(m) for m in _lista(fila["meses"])]
            if not all(1 <= m <= 12 for m in meses):
                raise ValueError(f"{fila['id']}: meses fuera de 1-12")
            lat, lon = float(fila["lat"]), float(fila["lon"])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError(f"{fila['id']}: coordenadas fuera de rango")
            parques.append(
                {
                    "id": fila["id"],
                    "nombre": fila["nombre"],
                    "pais": fila["pais"],
                    "continente": fila["continente"],
                    "wikidata": fila["wikidata"] or None,
                    "lat": lat,
                    "lon": lon,
                    "radio_km": float(fila["radio_km"]),
                    "tipos": tipos,
                    "meses": sorted(set(meses)),
                    "estrella": _lista(fila["estrella"]),
                    "tasa": fila["tasa"] or None,
                    "consejo": fila["consejo"],
                }
            )
    return parques
