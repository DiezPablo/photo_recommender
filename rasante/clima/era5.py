"""Descarga de ERA5 por punto (archivo de Open-Meteo) y resumen diario compacto.

Cada punto se descarga una vez (5 años horarios) y se guarda solo lo que usan los modelos: las nubes y el
tiempo en el pico de color del amanecer y del atardecer, la madrugada (niebla) y la noche (horas despejadas).
Open-Meteo cuenta una petición larga como varias llamadas (una por cada 14 días con ≤ 10 variables): con
5 años, ~130 llamadas por punto. El límite gratuito es de 10 000 al día y 5000 a la hora.
"""

from __future__ import annotations

import gzip
import io
import math
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from rasante.cielo import astro
from rasante.clima.rejilla import id_punto
from rasante.comun.red import sesion

ARCHIVO = "https://archive-api.open-meteo.com/v1/archive"
DESDE, HASTA = date(2021, 1, 1), date(2025, 12, 31)
VARIABLES = [
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "precipitation",
    "relative_humidity_2m",
    "wind_speed_10m",
]
TZ = ZoneInfo("Europe/Madrid")
DIR = Path("cache/clima")
# por hora no se pueden pasar 5000 llamadas: ~130 por punto → como mucho ~38 puntos a la hora
PAUSA_S = 100
DESPEJADO = 20  # % de nubosidad total por debajo del cual la hora cuenta como despejada


def coste(desde: date = DESDE, hasta: date = HASTA, variables: int = len(VARIABLES)) -> float:
    """Llamadas que Open-Meteo descuenta por una petición."""
    dias = (hasta - desde).days + 1
    return max(1.0, dias / 14) * max(1.0, variables / 10)


def descargar(lat: float, lon: float, desde: date = DESDE, hasta: date = HASTA) -> pd.DataFrame:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": desde.isoformat(),
        "end_date": hasta.isoformat(),
        "hourly": ",".join(VARIABLES),
        "timezone": "UTC",
    }
    s = sesion()
    for intento in range(6):
        try:
            r = s.get(ARCHIVO, params=params, timeout=300)
        except (requests.ConnectionError, requests.Timeout) as e:
            # cortes de conexión y esperas agotadas sueltos (proxies, TLS): se reintenta con espera creciente
            print(f"  conexión cortada ({e.__class__.__name__}): reintento", flush=True)
            time.sleep(10 * (intento + 1))
            continue
        if r.status_code == 429:
            espera = int(r.headers.get("Retry-After", 60 * (intento + 1)))
            print(f"  429 de Open-Meteo: espero {espera} s", flush=True)
            time.sleep(espera)
            continue
        r.raise_for_status()
        return horario(r.json())
    raise RuntimeError("ERA5 no responde")


def horario(respuesta: dict) -> pd.DataFrame:
    df = pd.DataFrame(respuesta["hourly"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.set_index("time").astype(float)


def _en(df: pd.DataFrame, t: datetime) -> dict:
    """Variables interpoladas en el instante t (UTC)."""
    t = pd.Timestamp(t).tz_convert("UTC")
    i = df.index.searchsorted(t)
    if i <= 0 or i >= len(df):
        return {}
    a, b = df.iloc[i - 1], df.iloc[i]
    w = (t - df.index[i - 1]) / (df.index[i] - df.index[i - 1])
    return {k: float(a[k] + (b[k] - a[k]) * w) for k in df.columns}


def _racha(valores: list[bool]) -> int:
    mejor = actual = 0
    for v in valores:
        actual = actual + 1 if v else 0
        mejor = max(mejor, actual)
    return mejor


def resumir(df: pd.DataFrame, lat: float, lon: float) -> pd.DataFrame:
    """Una fila por día: pico de color de amanecer y atardecer, madrugada y noche."""
    filas = []
    dias = sorted({t.astimezone(TZ).date() for t in df.index})
    for d in dias:
        sol = astro.calcular_sol(lat, lon, d, TZ)
        if not sol.amanecer or not sol.atardecer:
            continue
        fila: dict = {"fecha": d.isoformat(), "az_am": sol.az_amanecer, "az_at": sol.az_atardecer}
        for momento, t in (("am", sol.amanecer - timedelta(minutes=15)), ("at", sol.atardecer + timedelta(minutes=15))):
            v = _en(df, t)
            for k, col in (
                ("bajas", "cloud_cover_low"),
                ("medias", "cloud_cover_mid"),
                ("altas", "cloud_cover_high"),
                ("lluvia", "precipitation"),
                ("humedad", "relative_humidity_2m"),
                ("viento", "wind_speed_10m"),
            ):
                fila[f"{momento}_{k}"] = v.get(col, math.nan)
        # madrugada: de las 2 h a la salida del sol (como la previsión)
        ini = datetime(d.year, d.month, d.day, 2, tzinfo=TZ)
        madrugada = df.loc[ini.astimezone(UTC) : sol.amanecer.astimezone(UTC)]
        fila["hr_max"] = float(madrugada["relative_humidity_2m"].max()) if len(madrugada) else math.nan
        fila["viento_min"] = float(madrugada["wind_speed_10m"].min()) if len(madrugada) else math.nan
        # noche: de hora y media después de la puesta a hora y media antes de la salida del día siguiente
        manana = astro.calcular_sol(lat, lon, d + timedelta(days=1), TZ)
        if manana.amanecer:
            noche = df.loc[
                (sol.atardecer + timedelta(minutes=90)).astimezone(UTC) : (
                    manana.amanecer - timedelta(minutes=90)
                ).astimezone(UTC)
            ]
            fila["despejadas"] = _racha([c < DESPEJADO for c in noche["cloud_cover"]])
        filas.append(fila)
    return pd.DataFrame(filas)


def fichero(lat: float, lon: float, dir: Path = DIR) -> Path:
    return dir / f"{id_punto(lat, lon)}.csv.gz"


def guardar(resumen: pd.DataFrame, ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    texto = resumen.to_csv(index=False, float_format="%.1f")
    ruta.write_bytes(gzip.compress(texto.encode()))


def leer(ruta: Path) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(gzip.decompress(ruta.read_bytes())))
