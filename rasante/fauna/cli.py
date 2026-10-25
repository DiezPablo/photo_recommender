"""Spots de observación de fauna → fauna.json.

Uso:
  python -m rasante fauna --pbf spain-latest.osm.pbf --salida public/datos/fauna.json
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import requests

from rasante.comun.ficheros import escribir_json
from rasante.comun.ids import id_spot
from rasante.comun.territorio import Provincias, ccaa_de
from rasante.fauna import gbif
from rasante.fauna.osm import agrupar, leer_observatorios


def calcular(grupos: list[dict], provincias: Provincias | None = None) -> list[dict]:
    provincias = provincias or Provincias()
    nombres: dict[int, dict] = {}
    salida = []
    for i, g in enumerate(grupos):
        info = provincias.de(g["lat"], g["lon"])
        if info is None:  # en un país vecino
            continue
        try:
            r = gbif.resumen(g["lat"], g["lon"])
        except requests.RequestException as e:
            print(f"  sin GBIF para {g['nombre'] or g['osm']}: {e}")
            continue
        especies = []
        for clave, n in r["especies"]:
            if clave not in nombres:
                try:
                    nombres[clave] = gbif.nombre_comun(clave)
                except requests.RequestException:
                    nombres[clave] = {"cientifico": None, "clase": "ave", "nombre": None}
            especies.append({**nombres[clave], "n": n})
        nombre = g["nombre"] or (
            f"Observatorio junto a {g['cerca_de']}"
            if g.get("cerca_de")
            else f"Observatorio de fauna ({info['provincia']})"
        )
        salida.append(
            {
                "id": id_spot(nombre, g["lat"], g["lon"]),
                "nombre": nombre,
                "lat": g["lat"],
                "lon": g["lon"],
                "provincia": info["provincia"],
                "ccaa": ccaa_de(info["provincia"], info.get("ccaa")),
                "osm": g["osm"],
                "observatorios": g["observatorios"],
                "accesible": g["accesible"],
                "observaciones": r["observaciones"],
                "n_especies": r["n_especies"],
                "especies": especies,
                "meses": r["meses"],
            }
        )
        if i % 50 == 0:
            print(f"  {i}/{len(grupos)}", flush=True)
    return sorted(salida, key=lambda x: -x["observaciones"])


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="rasante fauna", description=__doc__.splitlines()[0])
    ap.add_argument("--pbf", type=Path, required=True)
    ap.add_argument("--salida", type=Path, default=Path("public/datos/fauna.json"))
    a = ap.parse_args(argv)
    t0 = time.time()
    grupos = agrupar(leer_observatorios(a.pbf))
    print(f"  {len(grupos)} zonas de observación", flush=True)
    lugares = calcular(grupos)
    escribir_json(
        a.salida,
        {
            "fuentes": {
                "lugares": "OpenStreetMap (ODbL)",
                "observaciones": f"GBIF.org, {gbif.DESDE_ANO}-{gbif.HASTA_ANO} (eBird, iNaturalist, Observation.org…)",
            },
            "lugares": lugares,
        },
    )
    print(f"{a.salida}: {len(lugares)} lugares ({time.time() - t0:.0f} s)")
