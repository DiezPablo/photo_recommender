"""Cliente de Open-Meteo (previsión y calidad del aire): gratuito y sin clave para uso no comercial.

Respeta sus límites (600 llamadas/min, 5000/h, 10 000/día; cuentan más con muchas variables) con un ritmo
de llamadas y una caché de 2 h, y reintenta los fallos puntuales.
"""

from __future__ import annotations

import json
import os
import time

import numpy as np
import pandas as pd
import requests

from rasante.comun.cache import CacheJson
from rasante.comun.red import USER_AGENT

CACHE = CacheJson(prefijo="om_", max_edad_s=2 * 3600)


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


AIRE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


# Open-Meteo cuenta 1 llamada por punto hasta 10 variables (gratis: 10 000 al día, 600 al minuto):
# en el spot se piden exactamente 10 y se derivan la nubosidad total y el punto de rocío.
VARS_SPOT = [
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "visibility",
    "precipitation_probability",
    "precipitation",
    "wind_speed_10m",
    "wind_gusts_10m",
    "relative_humidity_2m",
    "temperature_2m",
]


VARS_CAMINO = ["cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"]


NIVELES_HPA = (1000, 975, 950, 925, 900, 850, 800, 700)


VARS_PERFIL = [
    f"{v}_{p}hPa"
    for p in NIVELES_HPA
    for v in ("temperature", "relative_humidity", "cloud_cover", "geopotential_height")
] + ["total_column_integrated_water_vapour"]


VARS_ALT = ["cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"]


MODELO_ALT = "ecmwf_ifs025"


LLAMADAS_POR_MINUTO = 450


LOTE_COORDS = 100


def obtener(url: str, params: dict, obligatorio: bool = True):
    clave = url + json.dumps(params, sort_keys=True)
    datos = CACHE.leer(clave)
    if datos is not None:
        return datos
    for intento in range(5):
        try:
            r = requests.get(url, params=params, timeout=90, headers={"User-Agent": USER_AGENT})
        except requests.RequestException as e:  # cortes de conexión puntuales
            print(f"  {url.split('/')[2]}: {e.__class__.__name__}, reintento")
            time.sleep(5 * (intento + 1))
            continue
        if r.status_code in (429, 502, 503, 504):
            time.sleep(10 * (intento + 1))
            continue
        if r.status_code >= 400 and not obligatorio:
            print(f"  {url.split('/')[2]} respondió {r.status_code}: sigo sin esos datos")
            return None
        r.raise_for_status()
        try:
            datos = r.json()
        except ValueError:  # a veces responde 200 con el cuerpo vacío o cortado: se reintenta
            print(f"  {url.split('/')[2]}: respuesta no JSON, reintento")
            time.sleep(10 * (intento + 1))
            continue
        CACHE.guardar(clave, datos)
        return datos
    if obligatorio:
        raise SystemExit(f"{url} no responde")
    return None


def pedir(
    coords: list[tuple[float, float]],
    variables: list[str],
    dias: int,
    tz_nombre: str,
    url: str = OPEN_METEO_URL,
    extra: dict | None = None,
    obligatorio: bool = True,
) -> list[dict | None]:
    """Serie horaria para una lista de (lat, lon). Por coordenada: {"elevacion", "horas": DataFrame
    indexado por hora local (naive)}, o None si una API opcional no respondió."""
    out: list[dict | None] = []
    peso = max(1.0, len(variables) / 10)
    for i in range(0, len(coords), LOTE_COORDS):
        lote = coords[i : i + LOTE_COORDS]
        _ritmo(len(lote) * peso)
        params = {
            "latitude": ",".join(str(c[0]) for c in lote),
            "longitude": ",".join(str(c[1]) for c in lote),
            "hourly": ",".join(variables),
            "timezone": tz_nombre,
            "forecast_days": min(dias + 1, 16),
            **(extra or {}),
        }
        datos = obtener(url, params, obligatorio)
        if datos is None:
            out += [None] * len(lote)
            continue
        if isinstance(datos, dict):  # una sola coordenada → objeto, varias → lista
            datos = [datos]
        for d in datos:
            out.append(a_tabla(d))
    return out


_ventana_llamadas: list[tuple[float, float]] = []


LLAMADAS = {"total": 0.0}


def _ritmo(llamadas: float) -> None:
    """Respeta el límite por minuto de Open-Meteo (las llamadas se miden por punto y variables)."""
    if os.environ.get("SIN_RITMO"):
        return
    ahora = time.time()
    _ventana_llamadas[:] = [(t, n) for t, n in _ventana_llamadas if ahora - t < 60]
    usadas = sum(n for _, n in _ventana_llamadas)
    if usadas + llamadas > LLAMADAS_POR_MINUTO and _ventana_llamadas:
        espera = 60 - (ahora - _ventana_llamadas[0][0]) + 1
        time.sleep(max(0.0, espera))
        _ventana_llamadas.clear()
    _ventana_llamadas.append((time.time(), llamadas))
    LLAMADAS["total"] += llamadas


def a_tabla(d: dict) -> dict:
    df = pd.DataFrame(d["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").apply(pd.to_numeric, errors="coerce")
    # con models=… las columnas llevan el nombre del modelo como sufijo: se quita
    df.columns = [c.removesuffix(f"_{MODELO_ALT}") for c in df.columns]
    return {"elevacion": d.get("elevation"), "horas": derivar(df)}


def derivar(df: pd.DataFrame) -> pd.DataFrame:
    """Variables que no se piden para no pasar de 10 por punto."""
    if "cloud_cover" not in df and {"cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"} <= set(df):
        capas = df[["cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"]].fillna(0) / 100
        maximo = capas.max(axis=1)
        aleatorio = 1 - (1 - capas).prod(axis=1)
        # entre solapamiento máximo y aleatorio, como hacen los modelos
        df["cloud_cover"] = 100 * (maximo + aleatorio) / 2
    if "dew_point_2m" not in df and {"temperature_2m", "relative_humidity_2m"} <= set(df):
        t, hr = df["temperature_2m"], df["relative_humidity_2m"].clip(lower=1)
        g = np.log(hr / 100) + 17.625 * t / (243.04 + t)  # Magnus
        df["dew_point_2m"] = 243.04 * g / (17.625 - g)
    return df
