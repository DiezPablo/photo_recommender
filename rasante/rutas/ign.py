"""Senderos homologados FEDME (GR, PR, SL; CC BY 4.0) y Caminos Naturales (MAPA) del servicio del IGN."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests

from rasante.comun.red import sesion

from .geometria import partes_unidas
from .metricas import tipo_ruta

SESION = sesion()


CACHE = Path("cache") / "rutas"


IGN = "https://nco.ign.es/server/rest/services/nco/{servicio}/MapServer/{capa}/query"


SERVICIOS_IGN = {"GR": ("GR", 1), "PR": ("PR", 1), "SL": ("SL", 1), "CN": ("CaminosNaturales", 1)}


def _ign(servicio: str, capa: int) -> list[dict]:
    """Todas las entidades de una capa del IGN en GeoJSON (paginado), con caché."""
    f = CACHE / f"ign_{servicio}_{capa}.json"
    if f.exists():
        return json.loads(f.read_text())
    url = IGN.format(servicio=servicio, capa=capa)
    feats, inicio = [], 0
    while True:
        for intento in range(5):
            try:
                r = SESION.get(
                    url,
                    params={
                        "where": "1=1",
                        "outFields": "*",
                        "outSR": 4326,
                        "f": "geojson",
                        "resultOffset": inicio,
                        "resultRecordCount": 200,
                    },
                    timeout=180,
                )
                r.raise_for_status()
                lote = r.json().get("features", [])
                break
            except (requests.RequestException, ValueError):
                time.sleep(5 * (intento + 1))
        else:
            raise RuntimeError(f"IGN {servicio} no responde")
        feats += lote
        if len(lote) < 200:
            break
        inicio += len(lote)
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(feats))
    return feats


def _limpio(v) -> str | None:
    v = (v or "").strip() if isinstance(v, str) else v
    return v or None


def leer_ign() -> list[dict]:
    rutas = []
    for clave, (servicio, capa) in SERVICIOS_IGN.items():
        try:
            feats = _ign(servicio, capa)
        except RuntimeError as e:
            print(f"      {e}: se sigue sin esa fuente", flush=True)
            continue
        for k, f in enumerate(feats):
            p = {k2.split(".")[-1].lower(): v for k2, v in (f.get("properties") or {}).items()}
            g = f.get("geometry") or {}
            if g.get("type") == "LineString":
                lineas = [g["coordinates"]]
            elif g.get("type") == "MultiLineString":
                lineas = g["coordinates"]
            else:
                continue
            nombre = _limpio(p.get("nombre"))
            if not nombre:
                continue
            ref = None
            m = re.match(r"^((?:GR|PR|SL)[- ][A-Z]{0,3}[- ]?\d+(?:\.\d+)?)", nombre)
            if m:
                ref = m.group(1)
            fuente = "mapa" if clave == "CN" else "fedme"
            pl = lineas[0]
            rutas.append(
                {
                    "sentido": (tuple(pl[0][:2]), tuple(lineas[-1][-1][:2])),
                    "id": f"{fuente}-{_limpio(p.get('id')) or p.get('objectid') or k}",
                    "fuente": fuente,
                    "nombre": nombre,
                    "ref": ref,
                    "red": None,
                    "operador": "FEDME" if fuente == "fedme" else "MAPA",
                    "web": _limpio(p.get("url_info")),
                    "desde": None,
                    "hasta": None,
                    "descripcion": None,
                    "circular_tag": None,
                    "wikidata": None,
                    "tipo": "Camino Natural" if clave == "CN" else tipo_ruta(ref, nombre, None, {}),
                    "tramos": partes_unidas([[tuple(c[:2]) for c in linea] for linea in lineas]),
                }
            )
        print(f"      IGN {clave}: {len(feats)}", flush=True)
    return rutas
