"""comun.py — Utilidades compartidas por el pipeline."""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path

USER_AGENT = ("spots-paisaje/0.3 (https://github.com/DiezPablo/photo_recommender; "
              "proyecto personal no comercial)")


def id_spot(nombre: str, lat: float, lon: float) -> str:
    """Identificador estable y legible para URLs: 'mirador-de-la-barranca-3f9a'."""
    base = unicodedata.normalize("NFKD", nombre if isinstance(nombre, str) and nombre else "spot").encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:48].strip("-") or "spot"
    h = hashlib.sha1(f"{lat:.4f},{lon:.4f}".encode()).hexdigest()[:4]
    return f"{base}-{h}"


def limpiar_json(v):
    """Convierte NaN/inf y tipos numpy en valores JSON válidos (null o números nativos)."""
    if isinstance(v, dict):
        return {k: limpiar_json(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [limpiar_json(x) for x in v]
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):   # numpy escalares
        v = v.item()
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def escribir_json(ruta: Path, datos, indent: int | None = None) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(limpiar_json(datos), ensure_ascii=False, indent=indent,
                               allow_nan=False, separators=None if indent else (",", ":")))
