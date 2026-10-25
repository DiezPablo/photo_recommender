"""Alineaciones de sol y luna con los picos del horizonte de cada spot → alineaciones.json.

Uso:
  python -m rasante alineaciones                                   # spots de public/datos/spots.geojson
  python -m rasante alineaciones --dias 365 --salida salida/alineaciones.json
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from rasante.comun.ficheros import escribir_json
from rasante.eventos import alineaciones


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="rasante alineaciones", description=__doc__.splitlines()[0])
    ap.add_argument("--spots", type=Path, default=Path("public/datos/spots.geojson"))
    ap.add_argument("--salida", type=Path, default=Path("public/datos/alineaciones.json"))
    ap.add_argument("--dias", type=int, default=365)
    ap.add_argument("--hoy", type=date.fromisoformat, default=None)
    a = ap.parse_args(argv)
    hoy = a.hoy or datetime.now(alineaciones.zona(-3.7)).date()
    spots = [
        {**f["properties"], "lat": f["geometry"]["coordinates"][1], "lon": f["geometry"]["coordinates"][0]}
        for f in json.loads(a.spots.read_text())["features"]
    ]
    datos = alineaciones.calcular(spots, hoy, a.dias)
    escribir_json(
        a.salida,
        {
            "desde": hoy.isoformat(),
            "dias": a.dias,
            "tolerancia": alineaciones.TOLERANCIA,
            "spots": datos,
        },
    )
    print(f"{a.salida}: {sum(len(v) for v in datos.values())} alineaciones en {len(datos)} spots")
