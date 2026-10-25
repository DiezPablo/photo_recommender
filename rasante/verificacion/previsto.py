"""Previsión de Open-Meteo para los aeropuertos, resumida con los criterios de la verificación."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pandas as pd

from rasante.comun.red import sesion
from rasante.notas.niebla import prob_niebla_radiacion
from rasante.verificacion.aeropuertos import AEROPUERTOS
from rasante.verificacion.criterios import CUBIERTO, DESPEJADO, racha, ventanas

URL = "https://api.open-meteo.com/v1/forecast"
VARIABLES = ["cloud_cover_low", "cloud_cover_mid", "relative_humidity_2m", "wind_speed_10m", "visibility"]


def pedir(dias: int = 3) -> dict[str, pd.DataFrame]:
    """Una sola petición con todos los aeropuertos (Open-Meteo admite varias coordenadas)."""
    codigos = list(AEROPUERTOS)
    params = {
        "latitude": ",".join(str(AEROPUERTOS[c][0]) for c in codigos),
        "longitude": ",".join(str(AEROPUERTOS[c][1]) for c in codigos),
        "hourly": ",".join(VARIABLES),
        "forecast_days": dias + 1,
        "timezone": "UTC",
    }
    r = sesion().get(URL, params=params, timeout=120)
    r.raise_for_status()
    datos = r.json()
    return {c: tabla(d) for c, d in zip(codigos, datos if isinstance(datos, list) else [datos], strict=True)}


def tabla(d: dict) -> pd.DataFrame:
    df = pd.DataFrame(d["hourly"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.set_index("time").astype(float)


def _tramo(df: pd.DataFrame, ini: datetime, fin: datetime) -> pd.DataFrame:
    return df.loc[ini.astimezone(UTC) : fin.astimezone(UTC)]


def resumir(df: pd.DataFrame, lat: float, lon: float, d: date) -> dict | None:
    v = ventanas(lat, lon, d)
    if v is None:
        return None
    mad, ata, noc = (_tramo(df, *v[k]) for k in ("madrugada", "atardecer", "noche"))
    if mad.empty or ata.empty or noc.empty:
        return None
    p, _ = prob_niebla_radiacion(mad.to_dict("records"))
    tapado = float(ata[["cloud_cover_low", "cloud_cover_mid"]].max(axis=1).mean())
    despejadas = racha(list(noc[["cloud_cover_low", "cloud_cover_mid"]].max(axis=1) < DESPEJADO))
    return {"niebla": round(p, 3), "tapado": round(tapado), "cubierto": tapado >= CUBIERTO, "despejadas": despejadas}


def prevision(hoy: date, dias: int = 3, tablas: dict[str, pd.DataFrame] | None = None) -> list[dict]:
    """Lo previsto hoy para los próximos `dias` días en cada aeropuerto."""
    tablas = tablas or pedir(dias)
    filas = []
    for codigo, df in tablas.items():
        lat, lon = AEROPUERTOS[codigo]
        for k in range(1, dias + 1):
            d = hoy + timedelta(days=k)
            r = resumir(df, lat, lon, d)
            if r:
                filas.append({"emitida": hoy.isoformat(), "oaci": codigo, "fecha": d.isoformat(), **r})
    return filas


def hoy_utc() -> date:
    return datetime.now(UTC).date()
