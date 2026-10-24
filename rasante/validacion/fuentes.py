"""Datos históricos para validar: fotos de Commons con fecha EXIF, ERA5 (archivo de Open-Meteo),
CAMS (aerosoles) y METAR de los aeropuertos de Madrid (Iowa Environmental Mesonet)."""

from __future__ import annotations

import contextlib
import re
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from rasante.cielo import astro
from rasante.comun.red import sesion

SESION = sesion()


DESDE, HASTA = date(2016, 1, 1), date(2025, 12, 31)
COMMONS = "https://commons.wikimedia.org/w/api.php"


ARCHIVO = "https://archive-api.open-meteo.com/v1/archive"


AIRE = "https://air-quality-api.open-meteo.com/v1/air-quality"


CENTRO = (40.4168, -3.7038)  # Puerta del Sol


TZ = ZoneInfo("Europe/Madrid")


# Búsquedas de texto en Commons: devuelven fotos de puestas/salidas de sol de la zona. El filtro
# que de verdad decide es la hora EXIF (dentro de la ventana de color de ese día).
BUSQUEDAS = [
    "sunset Madrid",
    "atardecer Madrid",
    "puesta de sol Madrid",
    "sunrise Madrid",
    "amanecer Madrid",
    "sunset Segovia",
    "atardecer Segovia",
    "sunset Guadarrama",
    "atardecer Guadarrama",
    "sunset Templo de Debod",
    "atardecer Templo de Debod",
    "Madrid sky sunset clouds",
    "sunset Navacerrada",
    "amanecer sierra Madrid",
    "sunrise Segovia",
    "atardecer El Escorial",
    "Madrid skyline sunset",
    "Cuatro Torres sunset",
    "Casa de Campo atardecer",
    "Madrid at dusk",
    "Madrid twilight",
    "Madrid golden hour",
    "cielo Madrid nubes",
    "ocaso Madrid",
    "crepúsculo Madrid",
    "Madrid evening sky",
    "Madrid red sky",
]


# (sin Toledo: "sunset Toledo" devuelve sobre todo Toledo, Ohio)
AZ_ATARDECER = (240, 255, 270, 285, 300)


AZ_AMANECER = (60, 75, 90, 105, 120)


def consultar(params: dict) -> dict:
    params = {"action": "query", "format": "json", "formatversion": 2, "maxlag": 5, **params}
    for intento in range(10):
        r = SESION.get(COMMONS, params=params, timeout=60)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(int(r.headers.get("Retry-After", 0) or 10 * (intento + 1)))
            continue
        d = r.json()
        if "error" in d and d["error"].get("code") in ("maxlag", "ratelimited"):
            time.sleep(10 * (intento + 1))
            continue
        time.sleep(0.5)
        return d
    raise RuntimeError("Commons no responde")


def buscar_ficheros(consulta: str, maximo: int = 1500) -> set[str]:
    titulos: set[str] = set()
    offset = 0
    while offset < maximo:
        d = consultar(
            {
                "list": "search",
                "srsearch": consulta,
                "srnamespace": 6,
                "srlimit": 500,
                "sroffset": offset,
                "srwhat": "text",
            }
        )
        res = d.get("query", {}).get("search", [])
        titulos |= {r["title"] for r in res if re.search(r"\.(jpe?g|png|tiff?|webp)$", r["title"], re.I)}
        if "continue" not in d or not res:
            break
        offset = d["continue"].get("sroffset", offset + 500)
    return titulos


def fechas_exif(titulos: list[str]) -> list[datetime]:
    out = []
    for i in range(0, len(titulos), 50):
        d = consultar(
            {
                "titles": "|".join(titulos[i : i + 50]),
                "prop": "imageinfo",
                "iiprop": "extmetadata",
                "iiextmetadatafilter": "DateTimeOriginal",
            }
        )
        for p in d.get("query", {}).get("pages", []):
            meta = (p.get("imageinfo") or [{}])[0].get("extmetadata") or {}
            v = meta.get("DateTimeOriginal", {}).get("value", "") if isinstance(meta, dict) else ""
            m = re.search(r"(\d{4})[-:](\d{2})[-:](\d{2})[ T](\d{2}):(\d{2})", re.sub(r"<[^>]+>", "", v))
            if m:
                with contextlib.suppress(ValueError):
                    out.append(datetime(*map(int, m.groups()), tzinfo=TZ))
    return out


def dias_positivos() -> dict[tuple[str, str], int]:
    """(fecha, momento) → nº de fotos hechas en la ventana de color (EXIF en hora local)."""
    titulos: set[str] = set()
    for c in BUSQUEDAS:
        try:
            n = buscar_ficheros(c)
        except (RuntimeError, requests.RequestException):
            n = set()
        print(f"  «{c}»: {len(n)} ficheros", flush=True)
        titulos |= n
    fechas = fechas_exif(sorted(titulos))
    print(f"  {len(titulos)} ficheros distintos, {len(fechas)} con fecha EXIF", flush=True)
    pos: dict[tuple[str, str], int] = defaultdict(int)
    for t in fechas:
        if not (DESDE <= t.date() <= HASTA):
            continue
        sol = astro.calcular_sol(*CENTRO, t.date(), TZ)
        if sol.atardecer and timedelta(minutes=-50) <= t - sol.atardecer <= timedelta(minutes=40):
            pos[(t.date().isoformat(), "atardecer")] += 1
        elif sol.amanecer and timedelta(minutes=-40) <= t - sol.amanecer <= timedelta(minutes=50):
            pos[(t.date().isoformat(), "amanecer")] += 1
    # Fotos de paisaje geolocalizadas en la Sierra hechas en la ventana de color (del volcado de
    # descubrimiento antiguo de la Sierra; ver rasante/recursos/positivos_sierra.csv)
    extra = Path(__file__).resolve().parent.parent / "recursos" / "positivos_sierra.csv"
    if extra.exists():
        n0 = len(pos)
        for r in pd.read_csv(extra).itertuples():
            pos[(r.t[:10], r.momento)] += 1
        print(f"  +{len(pos) - n0} días de fotos de la Sierra en la ventana de color", flush=True)
    return dict(pos)


def era5(lat: float, lon: float, variables: list[str]) -> pd.DataFrame:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": DESDE.isoformat(),
        "end_date": HASTA.isoformat(),
        "hourly": ",".join(variables),
        "timezone": "Europe/Madrid",
    }
    for intento in range(6):
        r = SESION.get(ARCHIVO, params=params, timeout=300)
        if r.status_code == 429:
            time.sleep(60 * (intento + 1))
            continue
        r.raise_for_status()
        d = r.json()["hourly"]
        df = pd.DataFrame(d)
        df["time"] = pd.to_datetime(df["time"])
        return df.set_index("time")
    raise RuntimeError("ERA5 no responde")


def aire_historico() -> pd.DataFrame | None:
    params = {
        "latitude": CENTRO[0],
        "longitude": CENTRO[1],
        "start_date": "2016-01-01",
        "end_date": HASTA.isoformat(),
        "hourly": "aerosol_optical_depth,dust",
        "timezone": "Europe/Madrid",
    }
    try:
        r = SESION.get(AIRE, params=params, timeout=300)
        r.raise_for_status()
        df = pd.DataFrame(r.json()["hourly"])
    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"  sin aerosoles históricos: {e}")
        return None
    df["time"] = pd.to_datetime(df["time"])
    return df.set_index("time")


def en(df: pd.DataFrame | None, t: datetime) -> dict:
    if df is None:
        return {}
    t = pd.Timestamp(t.replace(tzinfo=None))
    i = df.index.searchsorted(t)
    if i <= 0 or i >= len(df):
        return {}
    a, b = df.iloc[i - 1], df.iloc[i]
    w = (t - df.index[i - 1]) / (df.index[i] - df.index[i - 1])
    return {k: a[k] + (b[k] - a[k]) * w for k in df.columns}


METAR = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"


AEROPUERTOS = {"LEMD": (40.472, -3.561), "LEGT": (40.294, -3.724), "LEVS": (40.370, -3.785), "LETO": (40.497, -3.446)}


def metar(estacion: str) -> pd.DataFrame:
    """Observaciones METAR (Iowa Environmental Mesonet): fenómenos y visibilidad (millas)."""
    params = {
        "station": estacion,
        "data": ["wxcodes", "vsby"],
        "year1": DESDE.year,
        "month1": 1,
        "day1": 1,
        "year2": HASTA.year,
        "month2": 12,
        "day2": 31,
        "tz": "Europe/Madrid",
        "format": "onlycomma",
        "latlon": "no",
        "missing": "empty",
        "trace": "empty",
        "direct": "no",
        "report_type": [3, 4],
    }
    r = SESION.get(METAR, params=params, timeout=600)
    r.raise_for_status()
    from io import StringIO

    df = pd.read_csv(StringIO(r.text))
    df["valid"] = pd.to_datetime(df["valid"])
    return df.set_index("valid").sort_index()
