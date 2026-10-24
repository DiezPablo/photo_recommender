"""Lectura de las series horarias: valor interpolado en un instante, tramos y perfil vertical."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from .openmeteo import NIVELES_HPA


def en(df: pd.DataFrame | None, t: datetime) -> dict:
    """Valores interpolados linealmente al instante t (el modelo es horario y el pico de color no
    cae en punto)."""
    if df is None or df.empty:
        return {}
    t = pd.Timestamp(t.replace(tzinfo=None))
    i = df.index.searchsorted(t)
    if i <= 0:
        return df.iloc[0].to_dict()
    if i >= len(df):
        return df.iloc[-1].to_dict()
    t0, t1 = df.index[i - 1], df.index[i]
    w = (t - t0) / (t1 - t0)
    a, b = df.iloc[i - 1], df.iloc[i]
    return {k: (a[k] if pd.isna(b[k]) else b[k] if pd.isna(a[k]) else a[k] + (b[k] - a[k]) * w) for k in df.columns}


def filas_entre(df: pd.DataFrame, ini: datetime, fin: datetime) -> pd.DataFrame:
    return df.loc[pd.Timestamp(ini.replace(tzinfo=None)) : pd.Timestamp(fin.replace(tzinfo=None))]


def suma_entre(df: pd.DataFrame, col: str, ini: datetime, fin: datetime) -> float:
    x = filas_entre(df, ini, fin)
    return float(x[col].sum()) if col in x and not x.empty else 0.0


def perfil_en(df: pd.DataFrame | None, t: datetime, suelo: float | None = None) -> dict:
    """Perfil vertical (de abajo arriba) en el instante t, para puntuacion.capa_nubosa. Los niveles
    por debajo del suelo del punto son extrapolados por el modelo y se descartan."""
    f = en(df, t)
    niveles = []
    for p in NIVELES_HPA:
        z = f.get(f"geopotential_height_{p}hPa")
        if z is None or pd.isna(z) or (suelo is not None and z < suelo + 30):
            continue
        niveles.append(
            {
                "hpa": p,
                "z": float(z),
                "t": f.get(f"temperature_{p}hPa"),
                "hr": f.get(f"relative_humidity_{p}hPa"),
                "nubes": f.get(f"cloud_cover_{p}hPa"),
            }
        )
    return {"niveles": sorted(niveles, key=lambda x: x["z"])}
