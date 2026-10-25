"""¿Se puede volar un dron en cada spot? → dron.json.

Uso:
  python -m rasante dron --spots public/datos/spots.geojson --salida public/datos/dron.json
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import date
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

from rasante.comun.ficheros import escribir_json
from rasante.dron.zonas import CAPAS, clasificar, descargar

NIVELES = ("no", "permiso", "condiciones")  # de más a menos restrictivo; sin zonas, «libre»


class Capa:
    def __init__(self, nombre: str, features: list[dict]):
        validas = [f for f in features if f.get("geometry")]
        self.nombre = nombre
        self.geoms = [shape(f["geometry"]) for f in validas]
        self.props = [f.get("properties") or {} for f in validas]
        self.arbol = STRtree(self.geoms)

    def en(self, lat: float, lon: float) -> list[dict]:
        p = Point(lon, lat)
        return [self.props[i] for i in self.arbol.query(p) if self.geoms[i].covers(p)]


def calcular(spots: list[dict], capas: list[Capa]) -> dict:
    zonas: dict[str, dict] = {}
    por_spot: dict[str, dict] = {}
    for s in spots:
        ids = []
        for capa in capas:
            for props in capa.en(s["lat"], s["lon"]):
                z = clasificar(capa.nombre, props)
                if z is None:
                    continue
                # la misma zona sale en muchos spots: se guarda una vez
                zid = f"{capa.nombre}:{z['nombre']}:{hash(z['texto']) & 0xFFFFFFFF:x}"
                zonas.setdefault(zid, {k: v for k, v in z.items() if v is not None})
                if zid not in ids:
                    ids.append(zid)
        ids.sort(key=lambda i: NIVELES.index(zonas[i]["nivel"]))
        estado = zonas[ids[0]]["nivel"] if ids else "libre"
        por_spot[s["id"]] = {"estado": estado, "zonas": ids} if ids else {"estado": estado}
    # ids cortos y estables dentro del fichero
    corto = {zid: str(i) for i, zid in enumerate(sorted(zonas))}
    for v in por_spot.values():
        if "zonas" in v:
            v["zonas"] = [corto[z] for z in v["zonas"]]
    return {"zonas": {corto[k]: v for k, v in zonas.items()}, "spots": por_spot}


def leer_spots(ruta: Path) -> list[dict]:
    return [
        {"id": f["properties"]["id"], "lat": f["geometry"]["coordinates"][1], "lon": f["geometry"]["coordinates"][0]}
        for f in json.loads(ruta.read_text())["features"]
    ]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="rasante dron", description=__doc__.splitlines()[0])
    ap.add_argument("--spots", type=Path, default=Path("public/datos/spots.geojson"))
    ap.add_argument("--salida", type=Path, default=Path("public/datos/dron.json"))
    a = ap.parse_args(argv)
    t0 = time.time()
    capas = []
    for nombre in CAPAS:
        features = descargar(nombre)
        print(f"  {nombre}: {len(features)} zonas", flush=True)
        capas.append(Capa(nombre, features))
    datos = calcular(leer_spots(a.spots), capas)
    estados = [v["estado"] for v in datos["spots"].values()]
    escribir_json(
        a.salida,
        {
            "fecha": date.today().isoformat(),
            "fuentes": {
                "uas": "ENAIRE, zonas geográficas de UAS (RD 517/2024)",
                "protegidos": "Agencia Europea de Medio Ambiente: espacios protegidos (NatDA) y Red Natura 2000",
            },
            **datos,
        },
    )
    resumen = ", ".join(f"{e} {estados.count(e)}" for e in (*NIVELES, "libre"))
    print(f"{a.salida}: {len(estados)} spots ({resumen}), {len(datos['zonas'])} zonas ({time.time() - t0:.0f} s)")
