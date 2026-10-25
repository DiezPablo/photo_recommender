"""Lo observado en los aeropuertos (METAR del Iowa Environmental Mesonet) con los mismos criterios."""

from __future__ import annotations

from datetime import date, timedelta
from io import StringIO

import pandas as pd

from rasante.comun.red import sesion
from rasante.verificacion.aeropuertos import AEROPUERTOS
from rasante.verificacion.criterios import racha, ventanas

URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
NIEBLA_MILLAS = 0.62  # 1 km
TAPAN = {"BKN", "OVC", "VV"}


def pedir(desde: date, hasta: date) -> pd.DataFrame:
    params = [
        *(("station", c) for c in AEROPUERTOS),
        *(("data", x) for x in ("wxcodes", "vsby", "skyc1", "skyc2", "skyc3", "skyc4")),
        ("year1", desde.year), ("month1", desde.month), ("day1", desde.day),
        ("year2", hasta.year), ("month2", hasta.month), ("day2", hasta.day),
        ("tz", "UTC"), ("format", "onlycomma"), ("latlon", "no"), ("missing", "empty"),
        ("trace", "empty"), ("direct", "no"), ("report_type", 3), ("report_type", 4),
    ]  # fmt: skip
    r = sesion().get(URL, params=params, timeout=300)
    r.raise_for_status()
    return leer(r.text)


def leer(csv: str) -> pd.DataFrame:
    df = pd.read_csv(StringIO(csv), dtype=str)
    df["valid"] = pd.to_datetime(df["valid"], utc=True)
    df["vsby"] = pd.to_numeric(df["vsby"], errors="coerce")
    return df


def _tapado(fila) -> bool:
    return any(str(fila.get(f"skyc{i}", "")).strip() in TAPAN for i in range(1, 5))


def resumir(df: pd.DataFrame, lat: float, lon: float, d: date) -> dict | None:
    """df: METAR de una estación (UTC)."""
    v = ventanas(lat, lon, d)
    if v is None:
        return None
    tramo = {k: df[(df["valid"] >= a) & (df["valid"] <= b)] for k, (a, b) in v.items()}
    if any(t.empty for t in tramo.values()):
        return None
    mad = tramo["madrugada"]
    niebla = bool(mad["wxcodes"].fillna("").str.contains(r"\bFG\b").any() or (mad["vsby"] < NIEBLA_MILLAS).any())
    ata = tramo["atardecer"]
    cubierto = sum(_tapado(f) for f in ata.to_dict("records")) > len(ata) / 2
    # de noche, por horas: una hora despejada si ningún parte de esa hora trae BKN/OVC
    noc = tramo["noche"].copy()
    noc["hora"] = noc["valid"].dt.floor("h")
    por_hora = noc.groupby("hora").apply(
        lambda g: not any(_tapado(f) for f in g.to_dict("records")), include_groups=False
    )
    return {"niebla": niebla, "cubierto": cubierto, "despejadas": racha(list(por_hora))}


def observacion(desde: date, hasta: date, metar: pd.DataFrame | None = None) -> list[dict]:
    metar = pedir(desde - timedelta(days=1), hasta + timedelta(days=2)) if metar is None else metar
    filas = []
    for codigo, df in metar.groupby("station"):
        if codigo not in AEROPUERTOS:
            continue
        lat, lon = AEROPUERTOS[codigo]
        d = desde
        while d <= hasta:
            r = resumir(df, lat, lon, d)
            if r:
                filas.append({"oaci": codigo, "fecha": d.isoformat(), **r})
            d += timedelta(days=1)
    return filas
