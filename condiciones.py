#!/usr/bin/env python3
"""
condiciones.py — Nota diaria (0-10) de cada spot para foto de paisaje.

Lee los spots (salida/spots.geojson de descubrir_spots.py y, opcionalmente,
mis_spots.csv con tus spots propios), pide la previsión horaria a Open-Meteo y
calcula con astral la posición del sol y la luna. Para cada spot y día evalúa:

  - amanecer / atardecer: nubes por capas en el spot (lienzo de nubes altas y
    medias, nubes bajas que tapan) y nubes bajas en el HORIZONTE, a ~40 km en
    la dirección del sol: si allí hay un banco de nubes bajas, el sol no llega
    a iluminar desde abajo y el cielo no se enciende.
  - astro: nubosidad media durante la noche astronómica y luna (iluminación y
    tiempo sobre el horizonte).
  - niebla: humedad, diferencia temperatura-punto de rocío y viento antes del
    amanecer (nieblas en valles, mares de nubes vistos desde arriba).
  - extras: reflejos (viento muy flojo) en lagos, embalses y playas.

Uso:
  python condiciones.py                       # 3 días, spots en salida/spots.geojson
  python condiciones.py --dias 2 --spots salida/spots.geojson --mis-spots mis_spots.csv

mis_spots.csv (opcional): nombre,lat,lon[,momentos]   momentos = "atardecer;astro"

Salida: salida/informe.json (lo consume notificar.py) y un resumen por pantalla.
Open-Meteo es gratuito y sin clave para uso no comercial.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from astral import Observer
from astral import moon as amoon
from astral import sun as asun

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
VARIABLES = [
    "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high",
    "visibility", "precipitation_probability", "wind_speed_10m",
    "relative_humidity_2m", "dew_point_2m", "temperature_2m",
]
KM_HORIZONTE = 40          # distancia del punto de control del horizonte
LOTE_COORDS = 50           # coordenadas por petición a Open-Meteo
TIPOS_AGUA = {"lago", "embalse", "playa", "cascada"}
CACHE = Path("cache")


# ----------------------------------------------------------- utilidades ----
def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def punto_destino(lat, lon, azimut_deg, km):
    """Punto a `km` de (lat, lon) siguiendo el rumbo `azimut_deg` (0 = norte)."""
    R = 6371.0
    d = km / R
    b = math.radians(azimut_deg)
    la1, lo1 = math.radians(lat), math.radians(lon)
    la2 = math.asin(math.sin(la1) * math.cos(d) + math.cos(la1) * math.sin(d) * math.cos(b))
    lo2 = lo1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(la1),
                           math.cos(d) - math.sin(la1) * math.sin(la2))
    return round(math.degrees(la2), 4), round(math.degrees(lo2), 4)


def _hhmm(t: datetime | None) -> str:
    return t.strftime("%H:%M") if t else "—"


# ---------------------------------------------------------------- spots ----
def cargar_spots(geojson: Path | None, csv: Path | None) -> pd.DataFrame:
    filas = []
    if geojson and geojson.exists():
        for f in json.loads(geojson.read_text())["features"]:
            p = f["properties"]
            lon, lat = f["geometry"]["coordinates"]
            filas.append({
                "nombre": p.get("nombre") or f"Spot {p.get('spot_id')}",
                "lat": lat, "lon": lon,
                "tipo": p.get("tipo_osm") if isinstance(p.get("tipo_osm"), str) else None,
                "momentos": momentos_desde_estadisticas(p),
                "origen": p.get("origen") or "commons",   # commons (con fotos) u osm (mirador)
            })
    if csv and csv.exists():
        for r in pd.read_csv(csv).itertuples():
            m = getattr(r, "momentos", None)
            filas.append({
                "nombre": r.nombre, "lat": float(r.lat), "lon": float(r.lon),
                "tipo": getattr(r, "tipo", None) if isinstance(getattr(r, "tipo", None), str) else None,
                "momentos": (m.split(";") if isinstance(m, str) and m
                             else ["amanecer", "atardecer", "astro", "niebla"]),
                "origen": "propio",
            })
    if not filas:
        raise SystemExit("No hay spots: ejecuta descubrir_spots.py o crea mis_spots.csv")
    return pd.DataFrame(filas)


def momentos_desde_estadisticas(p: dict) -> list[str]:
    """Qué momentos evaluar según cuándo lo fotografía la gente (fechas de captura en Commons)."""
    m = []
    if (p.get("pct_amanecer") or 0) >= 15 or p.get("mejor_momento") == "amanecer":
        m.append("amanecer")
    if (p.get("pct_atardecer") or 0) >= 15 or p.get("mejor_momento") == "atardecer":
        m.append("atardecer")
    if (p.get("pct_noche") or 0) >= 10 or p.get("mejor_momento") == "noche":
        m.append("astro")
    if not m:
        m = ["amanecer", "atardecer"]
    m.append("niebla")  # barato de evaluar y a veces es la sorpresa del día
    return m


# ------------------------------------------------------------------ sol ----
@dataclass
class Sol:
    amanecer: datetime
    atardecer: datetime
    az_amanecer: float
    az_atardecer: float
    dorada_manana: tuple[datetime, datetime]
    dorada_tarde: tuple[datetime, datetime]
    azul_manana: tuple[datetime, datetime]
    azul_tarde: tuple[datetime, datetime]
    noche_ini: datetime | None   # anochecer astronómico (sol a -18°)
    noche_fin: datetime | None   # amanecer astronómico del día siguiente


def calcular_sol(lat, lon, dia: date, tz: ZoneInfo) -> Sol:
    o = Observer(latitude=lat, longitude=lon)
    s = asun.sun(o, date=dia, tzinfo=tz)
    try:
        noche_ini = asun.dusk(o, date=dia, tzinfo=tz, depression=18)
        noche_fin = asun.dawn(o, date=dia + timedelta(days=1), tzinfo=tz, depression=18)
    except ValueError:  # en verano y latitudes altas puede no haber noche astronómica
        noche_ini = noche_fin = None
    return Sol(
        amanecer=s["sunrise"], atardecer=s["sunset"],
        az_amanecer=asun.azimuth(o, s["sunrise"]),
        az_atardecer=asun.azimuth(o, s["sunset"]),
        dorada_manana=asun.golden_hour(o, dia, asun.SunDirection.RISING, tz),
        dorada_tarde=asun.golden_hour(o, dia, asun.SunDirection.SETTING, tz),
        azul_manana=asun.blue_hour(o, dia, asun.SunDirection.RISING, tz),
        azul_tarde=asun.blue_hour(o, dia, asun.SunDirection.SETTING, tz),
        noche_ini=noche_ini, noche_fin=noche_fin,
    )


def luna_en_ventana(lat, lon, ini: datetime, fin: datetime) -> tuple[float, float]:
    """(iluminación 0-1, fracción de la ventana con la luna sobre el horizonte)."""
    fase = amoon.phase(ini.date())                       # 0 = nueva, ~14 = llena
    ilum = (1 - math.cos(2 * math.pi * fase / 29.53)) / 2
    o = Observer(latitude=lat, longitude=lon)
    muestras, arriba = 0, 0
    t = ini
    while t <= fin:
        muestras += 1
        arriba += amoon.elevation(o, t) > 0
        t += timedelta(minutes=30)
    return ilum, (arriba / muestras if muestras else 0.0)


# -------------------------------------------------------------- tiempo ----
def _cache_get(clave, max_edad_s=3 * 3600):
    f = CACHE / f"om_{hashlib.sha1(clave.encode()).hexdigest()}.json"
    if f.exists() and time.time() - f.stat().st_mtime < max_edad_s:
        return json.loads(f.read_text())
    return None


def _cache_set(clave, datos):
    CACHE.mkdir(exist_ok=True)
    (CACHE / f"om_{hashlib.sha1(clave.encode()).hexdigest()}.json").write_text(json.dumps(datos))


def pedir_tiempo(coords: list[tuple[float, float]], dias: int, tz_nombre: str) -> list[pd.DataFrame]:
    """Previsión horaria para una lista de (lat, lon). Devuelve un DataFrame por coordenada,
    indexado por hora local (naive)."""
    resultados: list[pd.DataFrame] = []
    for i in range(0, len(coords), LOTE_COORDS):
        lote = coords[i:i + LOTE_COORDS]
        params = {
            "latitude": ",".join(str(c[0]) for c in lote),
            "longitude": ",".join(str(c[1]) for c in lote),
            "hourly": ",".join(VARIABLES),
            "timezone": tz_nombre,
            "forecast_days": min(dias + 1, 16),
        }
        clave = json.dumps(params, sort_keys=True)
        datos = _cache_get(clave)
        if datos is None:
            r = requests.get(OPEN_METEO_URL, params=params, timeout=60)
            r.raise_for_status()
            datos = r.json()
            _cache_set(clave, datos)
        if isinstance(datos, dict):      # una sola coordenada → objeto, varias → lista
            datos = [datos]
        for d in datos:
            df = pd.DataFrame(d["hourly"])
            df["time"] = pd.to_datetime(df["time"])
            resultados.append(df.set_index("time"))
    return resultados


def fila_en(df: pd.DataFrame, t: datetime) -> pd.Series:
    """Fila de la hora más cercana a t."""
    t = pd.Timestamp(t.replace(tzinfo=None))
    return df.iloc[df.index.get_indexer([t], method="nearest")[0]]


def filas_entre(df: pd.DataFrame, ini: datetime, fin: datetime) -> pd.DataFrame:
    return df.loc[pd.Timestamp(ini.replace(tzinfo=None)):pd.Timestamp(fin.replace(tzinfo=None))]


# --------------------------------------------------------------- notas ----
def _v(fila, col, defecto=0.0):
    v = fila.get(col, defecto)
    return defecto if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


def nota_luz(local: pd.Series, horizonte: pd.Series) -> tuple[float, str]:
    """Amanecer/atardecer. Ideal: 30-70 % de nubes altas o medias, pocas bajas
    en el spot y horizonte despejado para que el sol las ilumine desde abajo."""
    L, M, H = _v(local, "cloud_cover_low"), _v(local, "cloud_cover_mid"), _v(local, "cloud_cover_high")
    Lh = _v(horizonte, "cloud_cover_low")
    P = _v(local, "precipitation_probability")
    V = _v(local, "visibility", 20000)

    lienzo = max(H, 0.8 * M)
    if lienzo <= 50:
        nota = 3 + 7 * lienzo / 50         # cielo despejado: correcto pero plano
    else:
        nota = 10 - 8 * (lienzo - 50) / 50  # cubierto de nubes altas: se apaga
    nota *= 1 - 0.7 * _clamp((L - 40) / 60)    # nubes bajas en el propio spot
    nota *= 1 - 0.8 * _clamp((Lh - 30) / 70)   # banco de nubes bajas en el horizonte
    nota *= 1 - 0.6 * P / 100
    if V < 3000:
        nota *= 0.6
    elif V < 10000:
        nota *= 0.85

    partes = [f"altas {H:.0f}% · medias {M:.0f}% · bajas {L:.0f}%",
              "horizonte despejado" if Lh < 30 else f"horizonte con bajas {Lh:.0f}%"]
    if P >= 30:
        partes.append(f"lluvia {P:.0f}%")
    if V < 10000:
        partes.append(f"visibilidad {V / 1000:.0f} km")
    return round(_clamp(nota, 0, 10), 1), " · ".join(partes)


def nota_astro(noche: pd.DataFrame, ilum: float, frac_luna: float) -> tuple[float, str]:
    if noche.empty:
        return 0.0, "sin noche astronómica"
    nubes = noche["cloud_cover"].mean()
    hum = noche["relative_humidity_2m"].mean()
    nota = 10 * (1 - nubes / 100) ** 1.5 * (1 - 0.85 * ilum * frac_luna)
    if hum > 90:
        nota *= 0.85    # rocío en la lente y calima
    detalle = (f"nubes {nubes:.0f}% · luna {ilum * 100:.0f}% iluminada, "
               f"{'fuera' if frac_luna < 0.1 else f'arriba el {frac_luna * 100:.0f}%'} de la noche")
    return round(_clamp(nota, 0, 10), 1), detalle


def nota_niebla(madrugada: pd.DataFrame) -> tuple[float, str]:
    if madrugada.empty:
        return 0.0, ""
    mejor, detalle = 0.0, ""
    for t, f in madrugada.iterrows():
        rh, temp, td = _v(f, "relative_humidity_2m"), _v(f, "temperature_2m"), _v(f, "dew_point_2m")
        viento = _v(f, "wind_speed_10m")
        n = 10 * _clamp((rh - 85) / 12) * _clamp((3 - (temp - td)) / 3) * _clamp((15 - viento) / 12)
        if n > mejor:
            mejor = n
            detalle = f"humedad {rh:.0f}% · T-Td {temp - td:.1f}° · viento {viento:.0f} km/h a las {t:%H:%M}"
    return round(mejor, 1), detalle


# ------------------------------------------------------------- informe ----
def evaluar(spots: pd.DataFrame, dias: int, tz_nombre: str, hoy: date | None = None) -> list[dict]:
    tz = ZoneInfo(tz_nombre)
    hoy = hoy or datetime.now(tz).date()
    fechas = [hoy + timedelta(days=i) for i in range(dias)]

    # Coordenadas a pedir: cada spot + sus puntos de horizonte (amanecer y atardecer).
    # El azimut del sol cambia muy poco en unos días: usamos el del primer día.
    coords, idx = [], []
    for s in spots.itertuples():
        sol0 = calcular_sol(s.lat, s.lon, fechas[0], tz)
        puntos = {
            "spot": (round(s.lat, 4), round(s.lon, 4)),
            "hz_amanecer": punto_destino(s.lat, s.lon, sol0.az_amanecer, KM_HORIZONTE),
            "hz_atardecer": punto_destino(s.lat, s.lon, sol0.az_atardecer, KM_HORIZONTE),
        }
        pos = {}
        for k, c in puntos.items():
            pos[k] = len(coords)
            coords.append(c)
        idx.append(pos)
    previsiones = pedir_tiempo(coords, dias, tz_nombre)

    resultados = []
    for s, pos in zip(spots.itertuples(), idx):
        df = previsiones[pos["spot"]]
        for dia in fechas:
            sol = calcular_sol(s.lat, s.lon, dia, tz)
            base = {"spot": s.nombre, "lat": s.lat, "lon": s.lon,
                    "tipo": s.tipo if isinstance(s.tipo, str) else None,
                    "origen": s.origen, "fecha": dia.isoformat()}

            if "amanecer" in s.momentos:
                f = fila_en(df, sol.amanecer)
                nota, det = nota_luz(f, fila_en(previsiones[pos["hz_amanecer"]], sol.amanecer))
                resultados.append({**base, "momento": "amanecer", "hora": _hhmm(sol.amanecer),
                                   "ventana": f"azul {_hhmm(sol.azul_manana[0])} · dorada hasta {_hhmm(sol.dorada_manana[1])}",
                                   "nota": nota, "detalle": det + _extra_reflejos(s.tipo, f)})

            if "atardecer" in s.momentos:
                f = fila_en(df, sol.atardecer)
                nota, det = nota_luz(f, fila_en(previsiones[pos["hz_atardecer"]], sol.atardecer))
                resultados.append({**base, "momento": "atardecer", "hora": _hhmm(sol.atardecer),
                                   "ventana": f"dorada desde {_hhmm(sol.dorada_tarde[0])} · azul hasta {_hhmm(sol.azul_tarde[1])}",
                                   "nota": nota, "detalle": det + _extra_reflejos(s.tipo, f)})

            if "astro" in s.momentos and sol.noche_ini and sol.noche_fin:
                ilum, frac = luna_en_ventana(s.lat, s.lon, sol.noche_ini, sol.noche_fin)
                nota, det = nota_astro(filas_entre(df, sol.noche_ini, sol.noche_fin), ilum, frac)
                resultados.append({**base, "momento": "astro",
                                   "hora": f"{_hhmm(sol.noche_ini)}–{_hhmm(sol.noche_fin)}",
                                   "ventana": "noche astronómica", "nota": nota, "detalle": det})

            if "niebla" in s.momentos:
                nota, det = nota_niebla(filas_entre(df, sol.amanecer - timedelta(hours=3),
                                                    sol.amanecer + timedelta(hours=1)))
                if nota >= 4:   # solo la reportamos cuando es probable
                    resultados.append({**base, "momento": "niebla", "hora": _hhmm(sol.amanecer),
                                       "ventana": "madrugada", "nota": nota, "detalle": det})
    return sorted(resultados, key=lambda r: (r["fecha"], -r["nota"]))


def _extra_reflejos(tipo, fila) -> str:
    viento = _v(fila, "wind_speed_10m", 99)
    if tipo in TIPOS_AGUA and viento < 6:
        return f" · viento {viento:.0f} km/h: posibles reflejos"
    return ""


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--spots", default="salida/spots.geojson")
    p.add_argument("--mis-spots", default="mis_spots.csv")
    p.add_argument("--dias", type=int, default=3)
    p.add_argument("--tz", default="Europe/Madrid")
    p.add_argument("--salida", default="salida/informe.json")
    p.add_argument("--top", type=int, default=5, help="mejores por día en pantalla")
    a = p.parse_args()

    spots = cargar_spots(Path(a.spots), Path(a.mis_spots))
    print(f"Evaluando {len(spots)} spots para {a.dias} días…")
    res = evaluar(spots, a.dias, a.tz)
    salida = Path(a.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps({"generado": datetime.now(ZoneInfo(a.tz)).isoformat(timespec="minutes"),
                                  "resultados": res}, ensure_ascii=False, indent=1, allow_nan=False))
    df = pd.DataFrame(res)
    for fecha, g in df.groupby("fecha"):
        print(f"\n== {fecha} ==")
        print(g.head(a.top)[["nota", "momento", "hora", "spot", "detalle"]].to_string(index=False))
    print(f"\nInforme completo en {salida}")


if __name__ == "__main__":
    main()
