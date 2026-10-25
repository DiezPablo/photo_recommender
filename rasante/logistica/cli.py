"""Logística de OpenStreetMap cerca de cada spot y de la salida de cada ruta → logistica.json.

Uso:
  python -m rasante logistica --pbf spain-latest.osm.pbf --spots public/datos/spots.geojson \\
      --rutas public/datos/rutas.json --salida public/datos/logistica.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rasante.comun.ficheros import escribir_json
from rasante.logistica.cercanos import RADIOS, Indice
from rasante.logistica.osm import leer_puntos


def calcular(puntos: list[dict], spots: list[dict], rutas: list[dict]) -> dict:
    ind = Indice(puntos)
    limpiar = lambda xs: [{k: v for k, v in x.items() if v is not None} for x in xs]
    return {
        "radios": {t: r for t, (r, _) in RADIOS.items()},
        "spots": {s["id"]: limpiar(c) for s in spots if (c := ind.cerca(s["lat"], s["lon"]))},
        "rutas": {r["id"]: limpiar(c) for r in rutas if (c := ind.cerca(r["inicio"][0], r["inicio"][1]))},
    }


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="rasante logistica", description=__doc__.splitlines()[0])
    ap.add_argument("--pbf", type=Path, required=True)
    ap.add_argument("--spots", type=Path, default=Path("public/datos/spots.geojson"))
    ap.add_argument("--rutas", type=Path, default=Path("public/datos/rutas.json"))
    ap.add_argument("--salida", type=Path, default=Path("public/datos/logistica.json"))
    a = ap.parse_args(argv)
    spots = [
        {"id": f["properties"]["id"], "lat": f["geometry"]["coordinates"][1], "lon": f["geometry"]["coordinates"][0]}
        for f in json.loads(a.spots.read_text())["features"]
    ]
    rutas = json.loads(a.rutas.read_text())["rutas"] if a.rutas.exists() else []
    print(f"Puntos útiles de {a.pbf}…", flush=True)
    datos = calcular(leer_puntos(a.pbf), spots, rutas)
    escribir_json(a.salida, datos)
    print(f"{a.salida}: {len(datos['spots'])} spots y {len(datos['rutas'])} rutas con algo cerca")
