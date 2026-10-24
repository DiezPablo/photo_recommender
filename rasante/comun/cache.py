"""Caché en disco de respuestas JSON, por clave (sha1). Respeta los límites de las APIs gratuitas y permite
repetir cálculos sin red. El formato de los ficheros (prefijo + sha1 + .json) no debe cambiar: GitHub Actions
guarda la caché entre ejecuciones (horas de peticiones a Commons)."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

RAIZ = Path("cache")


class CacheJson:
    def __init__(self, directorio: Path = RAIZ, prefijo: str = "", max_edad_s: float | None = None):
        self.directorio = Path(directorio)
        self.prefijo = prefijo
        self.max_edad_s = max_edad_s

    def _fichero(self, clave: str) -> Path:
        return self.directorio / f"{self.prefijo}{hashlib.sha1(clave.encode()).hexdigest()}.json"

    def leer(self, clave: str) -> Any | None:
        f = self._fichero(clave)
        if not f.exists():
            return None
        if self.max_edad_s is not None and time.time() - f.stat().st_mtime >= self.max_edad_s:
            return None
        return json.loads(f.read_text())

    def guardar(self, clave: str, datos: Any) -> None:
        self.directorio.mkdir(parents=True, exist_ok=True)
        self._fichero(clave).write_text(json.dumps(datos))
