"""Los mismos criterios para lo previsto y lo observado, día a día y por aeropuerto (hora local)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from rasante.cielo import astro

CUBIERTO = 70  # % de nubes bajas o medias (≈ BKN/OVC) que tapan el atardecer
DESPEJADO = 30  # % por debajo del cual una hora de noche cuenta como despejada (≈ sin BKN/OVC)
HORAS_NOCHE = 3


def zona(lon: float) -> ZoneInfo:
    return ZoneInfo("Atlantic/Canary" if lon < -12 else "Europe/Madrid")


def ventanas(lat: float, lon: float, d: date) -> dict[str, tuple[datetime, datetime]] | None:
    """Madrugada (2 h → salida del sol + 1 h), atardecer (± 45 min) y noche (puesta + 1,5 h → salida del día
    siguiente − 1,5 h), en hora local con zona."""
    tz = zona(lon)
    sol = astro.calcular_sol(lat, lon, d, tz)
    manana = astro.calcular_sol(lat, lon, d + timedelta(days=1), tz)
    if not (sol.amanecer and sol.atardecer and manana.amanecer):
        return None
    return {
        "madrugada": (datetime(d.year, d.month, d.day, 2, tzinfo=tz), sol.amanecer + timedelta(hours=1)),
        "atardecer": (sol.atardecer - timedelta(minutes=45), sol.atardecer + timedelta(minutes=45)),
        "noche": (sol.atardecer + timedelta(minutes=90), manana.amanecer - timedelta(minutes=90)),
    }


def racha(valores: list[bool]) -> int:
    mejor = actual = 0
    for v in valores:
        actual = actual + 1 if v else 0
        mejor = max(mejor, actual)
    return mejor
