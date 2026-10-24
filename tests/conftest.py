"""Fixtures compartidas: las pruebas no salen a internet (respuestas reales grabadas en tests/fixtures)."""

import json
import math
from datetime import date
from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures"
LP = {"zona": "3b", "sqm": 21.38, "bortle": 4, "descripcion": "rural con algo de resplandor"}


def sin_nan(obj) -> None:
    """Falla si hay NaN o infinitos en una estructura JSON."""
    if isinstance(obj, float):
        assert math.isfinite(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            sin_nan(v)
    elif isinstance(obj, list):
        for v in obj:
            sin_nan(v)


@pytest.fixture
def prevision_grabada(monkeypatch, tmp_path):
    """Open-Meteo (tiempo, perfil vertical, segundo modelo y CAMS) servido desde la grabación, caché vacía y
    contaminación lumínica fija. Devuelve el módulo de evaluación listo para usar."""
    from rasante.comun.cache import CacheJson
    from rasante.prevision import evaluacion, openmeteo

    monkeypatch.setattr(openmeteo, "CACHE", CacheJson(tmp_path / "cache", prefijo="om_"))
    monkeypatch.setattr(evaluacion, "contaminacion", lambda lat, lon: LP)
    monkeypatch.setattr(evaluacion, "cupula", lambda lat, lon, az: {"zona": "6a", "km": 20, "efectiva": 5.0})
    monkeypatch.setattr(openmeteo.requests, "get", lambda *a, **k: pytest.fail("petición de red inesperada"))
    grabacion = json.loads((FIX / "openmeteo_v2.json").read_text())["respuestas"]

    def obtener_grabado(url, params, obligatorio=True):
        clave = json.dumps({"url": url, **params}, sort_keys=True)
        assert clave in grabacion, f"petición no grabada: {params.get('hourly', '')[:60]}"
        return grabacion[clave]

    monkeypatch.setattr(openmeteo, "obtener", obtener_grabado)
    return evaluacion


@pytest.fixture
def informe(prevision_grabada):
    """Informe de 3 días con los mismos spots con los que se grabaron las respuestas."""
    spots = [
        {
            "id": "nav",
            "nombre": "Puerto de Navacerrada",
            "lat": 40.793,
            "lon": -4.011,
            "tipo": "mirador",
            "origen": "propio",
            "contaminacion": None,
        },
        {
            "id": "fis",
            "nombre": "Faro de Fisterra",
            "lat": 42.8823,
            "lon": -9.2718,
            "tipo": "faro",
            "origen": "propio",
            "contaminacion": None,
        },
    ]
    hoy = date.fromisoformat(json.loads((FIX / "openmeteo_v2.json").read_text())["hoy"])
    return prevision_grabada.evaluar(spots, 3, "Europe/Madrid", hoy=hoy)
