"""Mar en los spots de costa: mareas (pleamar y bajamar), nivel del mar y oleaje en el pico de luz.

Open-Meteo Marine (sin clave) da el nivel del mar con la marea (`sea_level_height_msl`) y el oleaje en la celda
de mar más cercana (~8 km). Es informativo: no entra en la nota (los pesos están validados), pero decide fotos
(As Catedrales solo con bajamar, reflejos en la arena mojada, larga exposición con mar en calma).
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
from shapely.geometry import Point, shape
from shapely.ops import unary_union

from rasante.comun.territorio import PROVINCIAS, VECINOS

from . import series
from .openmeteo import pedir

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
VARS_MAR = ["sea_level_height_msl", "wave_height", "wave_period", "wave_direction"]
TIPOS_COSTA = {"playa", "cabo", "faro", "acantilado"}
KM_COSTA, KM_COSTA_TIPO = 2.0, 5.0  # los polígonos de provincias están simplificados
# la rejilla del modelo de oleaje es de ~8 km: con 0,1° se comparten celdas y se ahorran llamadas
REDONDEO = 0.1
MAREA_PEQUENA_M = 0.4  # rango diario por debajo del cual la marea apenas se nota (Mediterráneo)


class Costa:
    """Línea de costa aproximada: el borde de las provincias que no es frontera con un país vecino."""

    def __init__(self):
        # con un pequeño margen: entre los polígonos simplificados quedan rendijas que, sin él, harían «costa»
        # de las fronteras entre provincias (el puerto de Navacerrada salía en la costa)
        provincias = [shape(f["geometry"]).buffer(0.01) for f in json.loads(PROVINCIAS.read_text())["features"]]
        tierra = unary_union(provincias).buffer(-0.01)
        vecinos = unary_union([shape(f["geometry"]) for f in json.loads(VECINOS.read_text())["features"]])
        self.linea = tierra.boundary.difference(vecinos.buffer(0.03))

    def km(self, lat: float, lon: float) -> float:
        return self.linea.distance(Point(lon, lat)) * 111.0  # grados → km (de sobra para umbrales de km)

    def es_costero(self, s: dict) -> bool:
        km = self.km(s["lat"], s["lon"])
        return km <= KM_COSTA or (km <= KM_COSTA_TIPO and (s.get("tipo") or "") in TIPOS_COSTA)


def pedir_mar(coords: list[tuple[float, float]], dias: int, tz_nombre: str) -> list[dict | None]:
    return pedir(coords, VARS_MAR, dias, tz_nombre, url=MARINE_URL, extra={"cell_selection": "sea"}, obligatorio=False)


def extremos(nivel: pd.Series) -> list[tuple[pd.Timestamp, str, float]]:
    """Pleamares y bajamares: máximos y mínimos locales de la serie horaria, afinados con una parábola."""
    v = nivel.dropna()
    salida = []
    for i in range(1, len(v) - 1):
        a, b, c = v.iloc[i - 1], v.iloc[i], v.iloc[i + 1]
        if (b > a and b >= c) or (b < a and b <= c):
            curv = a - 2 * b + c
            d = 0.5 * (a - c) / curv if curv else 0.0  # desplazamiento en horas (−0,5…0,5)
            t = v.index[i] + pd.Timedelta(hours=float(d))
            m = b - 0.25 * (a - c) * d
            salida.append((t, "alta" if b > a else "baja", float(m)))
    return salida


def _hhmm(t: pd.Timestamp, tz: ZoneInfo) -> str:
    """Hora en la zona del spot (las series vienen en la zona de `series.ZONA_SERIES`)."""
    return t.round("min").to_pydatetime().replace(tzinfo=series.ZONA_SERIES).astimezone(tz).strftime("%H:%M")


def _r(x, n=1):
    return None if x is None or pd.isna(x) else round(float(x), n)


def dia(df: pd.DataFrame | None, fecha: date, tz: ZoneInfo, momentos: dict[str, datetime | None]) -> dict | None:
    """Mareas del día, rango y, en cada momento (amanecer y atardecer), nivel, tendencia y oleaje."""
    if df is None or df.empty or df["sea_level_height_msl"].isna().all():
        return None
    ini = datetime.combine(fecha, datetime.min.time(), tz)
    fin = ini + timedelta(days=1)
    tramo = series.filas_entre(df, ini - timedelta(hours=2), fin + timedelta(hours=2))["sea_level_height_msl"]
    del_dia = [(t, tipo, m) for t, tipo, m in extremos(tramo) if series._local(ini) <= t < series._local(fin)]
    hoy = series.filas_entre(df, ini, fin)["sea_level_height_msl"].dropna()
    if len(hoy) < 20:  # el día no está entero en la serie (Open-Meteo Marine empieza hoy a las 00:00)
        return None
    rango = float(hoy.max() - hoy.min())
    salida: dict = {
        "rango_m": _r(rango),
        "mareas": [{"t": _hhmm(t, tz), "tipo": tipo, "m": _r(m)} for t, tipo, m in del_dia],
    }
    for nombre, t in momentos.items():
        if t is None:
            continue
        f = series.en(df, t)
        antes = series.en(df, t - timedelta(minutes=30)).get("sea_level_height_msl")
        nivel = f.get("sea_level_height_msl")
        x = {"olas_m": _r(f.get("wave_height")), "periodo_s": _r(f.get("wave_period"), 0)}
        if rango >= MAREA_PEQUENA_M and nivel is not None and not pd.isna(nivel):
            # posición entre bajamar (0) y pleamar (1) del día
            x["marea"] = round((nivel - hoy.min()) / rango, 2)
            if antes is not None and not pd.isna(antes):
                x["sube"] = bool(nivel > antes)
        salida[nombre] = x
    return salida
