"""Lo que se observa alrededor de un punto según GBIF: especies más vistas y observaciones por mes.

API pública de GBIF (sin clave). Se usan facetas (recuentos), no los registros: una petición por punto. Las
especies sensibles ya llegan con la ubicación generalizada por los propios conjuntos de datos.
"""

from __future__ import annotations

import json
import time
from collections import Counter

import requests

from rasante.comun.cache import CacheJson
from rasante.comun.red import sesion

API = "https://api.gbif.org/v1"
CLASES = {"aves": 212, "mamiferos": 359}
RADIO_GRADOS = 0.02  # ~2 km
DESDE_ANO, HASTA_ANO = 2016, 2025
# un mes: las observaciones cambian poco y la ejecución es mensual
CACHE = CacheJson(prefijo="gbif_", max_edad_s=25 * 86400)
_SESION = sesion()


def _get(ruta: str, params: dict | list) -> dict:
    clave = json.dumps({"ruta": ruta, "params": params if isinstance(params, dict) else [list(p) for p in params]})
    guardado = CACHE.leer(clave)
    if guardado is not None:
        return guardado
    for intento in range(5):
        try:
            r = _SESION.get(f"{API}/{ruta}", params=params, timeout=60)
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(5 * (intento + 1))
            continue
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After", 30)))
            continue
        r.raise_for_status()
        datos = r.json()
        CACHE.guardar(clave, datos)
        return datos
    raise requests.ConnectionError(f"GBIF no responde: {ruta}")


def resumen(lat: float, lon: float, max_especies: int = 12) -> dict:
    """Especies (clave de GBIF y nº de observaciones), nº de especies distintas y observaciones por mes."""
    params = [
        ("decimalLatitude", f"{lat - RADIO_GRADOS:.4f},{lat + RADIO_GRADOS:.4f}"),
        ("decimalLongitude", f"{lon - RADIO_GRADOS * 1.3:.4f},{lon + RADIO_GRADOS * 1.3:.4f}"),
        *(("classKey", c) for c in CLASES.values()),
        ("year", f"{DESDE_ANO},{HASTA_ANO}"),
        ("occurrenceStatus", "PRESENT"),
        ("limit", 0),
        ("facet", "speciesKey"),
        ("facet", "month"),
        ("speciesKey.facetLimit", 300),
        ("month.facetLimit", 12),
    ]
    d = _get("occurrence/search", params)
    facetas = {f["field"]: f["counts"] for f in d.get("facets", [])}
    especies = facetas.get("SPECIES_KEY", [])
    meses = [0] * 12
    for m in facetas.get("MONTH", []):
        meses[int(m["name"]) - 1] = m["count"]
    return {
        "observaciones": d.get("count", 0),
        "n_especies": len(especies),
        "especies": [(int(e["name"]), e["count"]) for e in especies[:max_especies]],
        "meses": meses,
    }


def nombre_comun(clave: int) -> dict:
    """Nombre científico, clase y el nombre en español más repetido (en minúscula salvo la inicial)."""
    sp = _get(f"species/{clave}", {})
    vn = _get(f"species/{clave}/vernacularNames", {"limit": 500})
    es = Counter(
        v["vernacularName"].strip().lower() for v in vn.get("results", []) if v.get("language") in ("spa", "es")
    )
    comun = es.most_common(1)[0][0] if es else None
    return {
        "cientifico": sp.get("canonicalName") or sp.get("scientificName"),
        "clase": "mamifero" if sp.get("classKey") == CLASES["mamiferos"] else "ave",
        "nombre": comun[0].upper() + comun[1:] if comun else None,
    }
