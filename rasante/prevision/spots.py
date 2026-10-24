"""Carga de los spots a evaluar: los descubiertos (spots.geojson) y los propios (mis_spots.csv)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import requests

from rasante.comun.ids import id_spot
from rasante.comun.territorio import Provincias, ccaa_de
from rasante.terreno import horizonte


def _relieve(lat: float, lon: float) -> dict | None:
    """Horizonte del terreno de un spot propio (los descubiertos ya lo traen calculado)."""
    try:
        return horizonte.perfil(lat, lon)
    except requests.RequestException:
        return None


def cargar_spots(geojson: Path | None, csv: Path | None) -> list[dict]:
    spots: list[dict] = []
    if geojson and geojson.exists():
        for f in json.loads(geojson.read_text())["features"]:
            p = f["properties"]
            lon, lat = f["geometry"]["coordinates"]
            nombre = p.get("nombre") or f"Spot {p.get('spot_id')}"
            spots.append(
                {
                    "id": p.get("id") or id_spot(nombre, lat, lon),
                    "nombre": nombre,
                    "lat": lat,
                    "lon": lon,
                    "tipo": p.get("tipo_osm"),
                    "origen": p.get("origen") or "commons",
                    "contaminacion": p.get("contaminacion"),
                    "relieve": p.get("horizonte"),
                    "provincia": p.get("provincia"),
                    "ccaa": ccaa_de(p.get("provincia"), p.get("ccaa")),
                }
            )
    if csv and csv.exists():
        df = pd.read_csv(csv, comment="#", skip_blank_lines=True)
        provincias = Provincias() if len(df) else None
        for r in df.itertuples():
            tipo = getattr(r, "tipo", None)
            lat, lon = float(r.lat), float(r.lon)
            info = provincias.de(lat, lon) if provincias else None
            spots.append(
                {
                    "id": id_spot(r.nombre, lat, lon),
                    "nombre": r.nombre,
                    "lat": lat,
                    "lon": lon,
                    "tipo": tipo if isinstance(tipo, str) else None,
                    "origen": "propio",
                    "contaminacion": None,
                    "relieve": _relieve(lat, lon),
                    "provincia": info["provincia"] if info else None,
                    "ccaa": ccaa_de(info["provincia"], info.get("ccaa")) if info else None,
                }
            )
    if not spots:
        raise SystemExit("No hay spots: ejecuta `python -m rasante spots` o añade alguno a mis_spots.csv")
    vistos, unicos = set(), []
    for s in spots:
        if s["id"] not in vistos:
            vistos.add(s["id"])
            unicos.append(s)
    return unicos
