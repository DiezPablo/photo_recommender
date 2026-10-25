"""Verificación diaria: guarda lo previsto para los aeropuertos, añade lo observado (METAR) y calcula el
marcador de aciertos → verificacion.json.

Uso:
  python -m rasante verificar --historial salida/verificacion.json   # lee el anterior si existe y lo amplía
"""

from __future__ import annotations

import argparse
import json
from datetime import timedelta
from pathlib import Path

import requests

from rasante.comun.ficheros import escribir_json
from rasante.verificacion import marcador, observado, previsto


def leer_historial(ruta: Path) -> dict:
    """El historial anterior; si no existe o está vacío o roto, se empieza de cero (nunca se para por esto)."""
    try:
        return json.loads(ruta.read_text())
    except (OSError, ValueError):
        return {}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="rasante verificar", description=__doc__.splitlines()[0])
    ap.add_argument("--historial", type=Path, default=Path("public/datos/verificacion.json"))
    a = ap.parse_args(argv)
    hoy = previsto.hoy_utc()
    historial = leer_historial(a.historial)
    nuevas, vistas = [], []
    try:
        nuevas = previsto.prevision(hoy)
    except requests.RequestException as e:
        print(f"  sin previsión para los aeropuertos: {e}")
    try:
        # los dos últimos días (el METAR de anoche ya está completo)
        vistas = observado.observacion(hoy - timedelta(days=3), hoy - timedelta(days=1))
    except requests.RequestException as e:
        print(f"  sin METAR: {e}")
    datos = marcador.fusionar(historial, nuevas, vistas, hoy)
    datos["marcador"] = marcador.marcador(datos, hoy)
    escribir_json(a.historial, datos)
    m = datos["marcador"]
    print(
        f"{a.historial}: {len(nuevas)} previsiones nuevas, {len(vistas)} observaciones; {m['casos']} casos en el marcador"
    )
