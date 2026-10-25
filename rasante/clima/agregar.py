"""De los resúmenes diarios de cada punto a probabilidades por mes, con los modelos de nota de la previsión.

El camino del sol (nubes bajas a 15, 40, 80 y 150 km hacia el sol) se toma de los puntos vecinos de la
rejilla, interpolando entre los cuatro que rodean cada punto del camino (si falta alguno, el más cercano a
menos de 0,35°; si no hay ninguno, ese tramo del camino no cuenta).
"""

from __future__ import annotations

import math
from collections import defaultdict

import pandas as pd

from rasante.cielo.astro import punto_destino
from rasante.clima.rejilla import PASO
from rasante.notas import nota_luz
from rasante.notas.luz import KM_CAMINO
from rasante.notas.niebla import prob_niebla_radiacion

NOTA_BUENA = 7.0
HORAS_NOCHE = 3  # una noche «despejada»: al menos 3 h seguidas sin nubes


def _rejilla(lat: float, lon: float) -> tuple[float, float]:
    return round(round(lat / PASO) * PASO, 2), round(round(lon / PASO) * PASO, 2)


def _valor_camino(datos: dict, lat: float, lon: float, fecha: str, momento: str) -> dict | None:
    """Nubes en un punto cualquiera a partir de los puntos de la rejilla que lo rodean."""
    la0 = math.floor(lat / PASO) * PASO
    lo0 = math.floor(lon / PASO) * PASO
    suma: dict[str, float] = defaultdict(float)
    peso_total = 0.0
    for la, wla in ((la0, 1 - (lat - la0) / PASO), (la0 + PASO, (lat - la0) / PASO)):
        for lo, wlo in ((lo0, 1 - (lon - lo0) / PASO), (lo0 + PASO, (lon - lo0) / PASO)):
            fila = datos.get((round(la, 2), round(lo, 2)), {}).get(fecha)
            if fila is None or math.isnan(fila[f"{momento}_bajas"]):
                continue
            w = wla * wlo
            for k in ("bajas", "medias", "altas"):
                suma[k] += w * fila[f"{momento}_{k}"]
            peso_total += w
    if peso_total < 0.5:
        # si faltan vecinos (costa, borde de la rejilla), el más cercano si está a menos de 0,35°
        cerca = _rejilla(lat, lon)
        fila = datos.get(cerca, {}).get(fecha)
        if fila is None or math.hypot(cerca[0] - lat, cerca[1] - lon) > 0.35:
            return None
        return {k: fila[f"{momento}_{k}"] for k in ("bajas", "medias", "altas")}
    return {k: v / peso_total for k, v in suma.items()}


def notas_punto(datos: dict, lat: float, lon: float) -> pd.DataFrame:
    """Nota de amanecer y atardecer, horas despejadas y probabilidad de niebla de cada día de un punto."""
    filas = []
    for fecha, f in datos[(lat, lon)].items():
        r = {"fecha": fecha, "despejadas": f.get("despejadas", math.nan)}
        for momento, nombre in (("am", "amanecer"), ("at", "atardecer")):
            if math.isnan(f[f"{momento}_bajas"]):
                r[nombre] = math.nan
                continue
            local = {
                "cloud_cover_low": f[f"{momento}_bajas"],
                "cloud_cover_mid": f[f"{momento}_medias"],
                "cloud_cover_high": f[f"{momento}_altas"],
                "precipitation": f[f"{momento}_lluvia"],
                # ERA5 no da probabilidad de lluvia: si llovía (> 0,2 mm/h) se trata como segura
                "precipitation_probability": 90 if f[f"{momento}_lluvia"] > 0.2 else 0,
                "relative_humidity_2m": f[f"{momento}_humedad"],
                "wind_speed_10m": f[f"{momento}_viento"],
            }
            camino = []
            for km in KM_CAMINO:
                la, lo = punto_destino(lat, lon, f[f"az_{momento}"], km)
                v = _valor_camino(datos, la, lo, fecha, momento)
                if v:
                    camino.append({"km": km, "low": v["bajas"], "mid": v["medias"], "high": v["altas"]})
            r[nombre] = nota_luz(local, camino, None, momento=nombre).valor
        if not math.isnan(f.get("hr_max", math.nan)):
            r["niebla"] = prob_niebla_radiacion(
                [{"relative_humidity_2m": f["hr_max"], "wind_speed_10m": f["viento_min"]}]
            )[0]
        filas.append(r)
    return pd.DataFrame(filas)


def por_mes(notas: pd.DataFrame) -> dict[str, list[int]]:
    """Porcentajes por mes (enero a diciembre): amaneceres y atardeceres buenos, noches despejadas, nieblas."""
    n = notas.copy()
    n["mes"] = pd.to_datetime(n["fecha"]).dt.month
    g = n.groupby("mes")

    def pct(serie):
        return [
            round(float(serie.get(m, math.nan)) * 100) if not math.isnan(serie.get(m, math.nan)) else None
            for m in range(1, 13)
        ]

    return {
        "amanecer": pct(g["amanecer"].apply(lambda s: (s.dropna() >= NOTA_BUENA).mean())),
        "atardecer": pct(g["atardecer"].apply(lambda s: (s.dropna() >= NOTA_BUENA).mean())),
        "noche": pct(g["despejadas"].apply(lambda s: (s.dropna() >= HORAS_NOCHE).mean())),
        "niebla": pct(g["niebla"].mean()) if "niebla" in n else [None] * 12,
    }


def cargar_datos(resumenes: dict[tuple[float, float], pd.DataFrame]) -> dict:
    """{(lat, lon): {fecha: fila}} para acceder rápido a los vecinos."""
    return {p: {r["fecha"]: r for r in df.to_dict("records")} for p, df in resumenes.items()}
