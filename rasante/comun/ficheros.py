"""Lectura y escritura de los ficheros de datos. Los JSON publicados no pueden llevar NaN ni infinitos."""

from __future__ import annotations

import json
import math
from pathlib import Path


def limpiar_json(v):
    """Convierte NaN/inf y tipos numpy en valores JSON válidos (null o números nativos)."""
    if isinstance(v, dict):
        return {k: limpiar_json(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [limpiar_json(x) for x in v]
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):  # numpy escalares
        v = v.item()
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def escribir_json(ruta: Path, datos, indent: int | None = None) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(
            limpiar_json(datos),
            ensure_ascii=False,
            indent=indent,
            allow_nan=False,
            separators=None if indent else (",", ":"),
        )
    )
