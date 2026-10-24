"""Identificadores estables y legibles para las URLs de los spots."""

from __future__ import annotations

import hashlib
import re
import unicodedata


def id_spot(nombre: str, lat: float, lon: float) -> str:
    """Identificador estable y legible para URLs: 'mirador-de-la-barranca-3f9a'."""
    base = (
        unicodedata.normalize("NFKD", nombre if isinstance(nombre, str) and nombre else "spot")
        .encode("ascii", "ignore")
        .decode()
    )
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:48].strip("-") or "spot"
    h = hashlib.sha1(f"{lat:.4f},{lon:.4f}".encode()).hexdigest()[:4]
    return f"{base}-{h}"
