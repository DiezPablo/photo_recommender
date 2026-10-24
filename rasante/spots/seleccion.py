"""Puntuación de los candidatos para elegir los spots: popularidad en Commons y Wikipedia, tipo de lugar y
cielo (los centros de ciudad acumulan fotos pero son malos para paisaje y nocturna)."""

from __future__ import annotations

import numpy as np
import requests

from rasante.cielo.contaminacion import contaminacion

PESO_TIPO = {
    "mirador": 1.0,
    "cabo": 0.8,
    "faro": 0.6,
    "acantilado": 0.6,
    "cumbre": 0.5,
    "lago": 0.6,
    "cascada": 0.4,
    "cañón": 0.6,
    "playa": 0.3,
    "embalse": 0.3,
}


def ajuste_cielo(lat: float, lon: float) -> float:
    """Penalización por cielo urbano (atlas de Lorenz): el recuento de fotos premia los centros de ciudad,
    que son malos sitios para paisaje y nocturna. Un icono urbano con cientos de fotos sigue entrando."""
    try:
        lp = contaminacion(lat, lon)
    except requests.RequestException:
        return 0.0
    if not lp:
        return 0.0
    sqm = lp["sqm"]
    return -1.6 if sqm < 18.5 else -0.9 if sqm < 19.5 else -0.3 if sqm < 20.5 else 0.3 if sqm >= 21.3 else 0.0


def entero(v) -> int:
    """Entero de un valor de pandas que puede ser None o NaN (NaN es «verdadero»: `NaN or 0` es NaN)."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0
    return int(v) if np.isfinite(v) else 0
