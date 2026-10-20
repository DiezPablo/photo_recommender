#!/usr/bin/env python3
"""
validar.py — Validación histórica de las notas de amanecer y atardecer.

¿Separa la nota los días en que el cielo se encendió de los demás? Como "verdad" se usan los días
en que alguien subió a Wikimedia Commons una foto de una puesta o salida de sol en Madrid o
Segovia, hecha en la ventana de color (fecha y hora EXIF). No es una verdad perfecta (también se
fotografían puestas mediocres y muchas buenas no se suben), pero es independiente del modelo.

Para cada día de 2016-2025 se calcula la nota con el tiempo real reanalizado (ERA5, vía el archivo
de Open-Meteo) en el centro de Madrid y en el camino del sol, con el modelo antiguo (v1) y el
nuevo (v2), y se mide el AUC: probabilidad de que un día fotografiado puntúe más que un día
cualquiera **del mismo mes** (0,5 = azar, 1 = perfecto). Se compara por mes para que no gane un
modelo solo por acertar la estación.

Uso: python validar.py [--salida salida/validacion]   (tarda: muchas peticiones a Commons y ERA5)
"""
from __future__ import annotations

import argparse
import json
import math
import re
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

import astro
from comun import USER_AGENT
from puntuacion import KM_CAMINO, _v, nota_luz

COMMONS = "https://commons.wikimedia.org/w/api.php"
ARCHIVO = "https://archive-api.open-meteo.com/v1/archive"
AIRE = "https://air-quality-api.open-meteo.com/v1/air-quality"
CENTRO = (40.4168, -3.7038)          # Puerta del Sol
TZ = ZoneInfo("Europe/Madrid")
DESDE, HASTA = date(2016, 1, 1), date(2025, 12, 31)
# Búsquedas de texto en Commons: devuelven fotos de puestas/salidas de sol de la zona. El filtro
# que de verdad decide es la hora EXIF (dentro de la ventana de color de ese día).
BUSQUEDAS = ["sunset Madrid", "atardecer Madrid", "puesta de sol Madrid", "sunrise Madrid", "amanecer Madrid",
             "sunset Segovia", "atardecer Segovia", "sunset Guadarrama", "atardecer Guadarrama",
             "sunset Templo de Debod", "atardecer Templo de Debod", "Madrid sky sunset clouds",
             "sunset Navacerrada", "amanecer sierra Madrid", "sunrise Segovia", "atardecer El Escorial",
             "Madrid skyline sunset", "Cuatro Torres sunset", "Casa de Campo atardecer",
             "Madrid at dusk", "Madrid twilight", "Madrid golden hour", "cielo Madrid nubes", "ocaso Madrid",
             "crepúsculo Madrid", "Madrid evening sky", "Madrid red sky"]
# (sin Toledo: "sunset Toledo" devuelve sobre todo Toledo, Ohio)
AZ_ATARDECER = (240, 255, 270, 285, 300)
AZ_AMANECER = (60, 75, 90, 105, 120)
SESION = requests.Session()
SESION.headers["User-Agent"] = USER_AGENT


# -------------------------------------------------------------- Commons ----
def _commons(params: dict) -> dict:
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
        d = _commons({"list": "search", "srsearch": consulta, "srnamespace": 6, "srlimit": 500,
                      "sroffset": offset, "srwhat": "text"})
        res = d.get("query", {}).get("search", [])
        titulos |= {r["title"] for r in res if re.search(r"\.(jpe?g|png|tiff?|webp)$", r["title"], re.I)}
        if "continue" not in d or not res:
            break
        offset = d["continue"].get("sroffset", offset + 500)
    return titulos


def fechas_exif(titulos: list[str]) -> list[datetime]:
    out = []
    for i in range(0, len(titulos), 50):
        d = _commons({"titles": "|".join(titulos[i:i + 50]), "prop": "imageinfo", "iiprop": "extmetadata",
                      "iiextmetadatafilter": "DateTimeOriginal"})
        for p in d.get("query", {}).get("pages", []):
            meta = (p.get("imageinfo") or [{}])[0].get("extmetadata") or {}
            v = meta.get("DateTimeOriginal", {}).get("value", "") if isinstance(meta, dict) else ""
            m = re.search(r"(\d{4})[-:](\d{2})[-:](\d{2})[ T](\d{2}):(\d{2})", re.sub(r"<[^>]+>", "", v))
            if m:
                try:
                    out.append(datetime(*map(int, m.groups()), tzinfo=TZ))
                except ValueError:
                    pass
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
    # descubrir_spots.py; ver validacion/positivos_sierra.csv)
    extra = Path(__file__).parent / "validacion" / "positivos_sierra.csv"
    if extra.exists():
        n0 = len(pos)
        for r in pd.read_csv(extra).itertuples():
            pos[(r.t[:10], r.momento)] += 1
        print(f"  +{len(pos) - n0} días de fotos de la Sierra en la ventana de color", flush=True)
    return dict(pos)


# ----------------------------------------------------------------- ERA5 ----
def era5(lat: float, lon: float, variables: list[str]) -> pd.DataFrame:
    params = {"latitude": lat, "longitude": lon, "start_date": DESDE.isoformat(), "end_date": HASTA.isoformat(),
              "hourly": ",".join(variables), "timezone": "Europe/Madrid"}
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
    params = {"latitude": CENTRO[0], "longitude": CENTRO[1], "start_date": "2016-01-01",
              "end_date": HASTA.isoformat(), "hourly": "aerosol_optical_depth,dust", "timezone": "Europe/Madrid"}
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


# ------------------------------------------------------------ modelo v1 ----
def nota_luz_v1(local: dict, horizonte_bajas: float) -> float:
    """El modelo publicado hasta oct-2026 (puntuacion.py v1), para comparar."""
    L, M, H = _v(local, "cloud_cover_low"), _v(local, "cloud_cover_mid"), _v(local, "cloud_cover_high")
    P = _v(local, "precipitation_probability")
    lienzo = max(H, 0.8 * M)
    n = 4.0
    if lienzo < 15:
        n -= 1
    elif lienzo < 35:
        n += 1 + 2 * (lienzo - 15) / 20
    elif lienzo <= 70:
        n += 4
    else:
        n += 4 - 6 * (lienzo - 70) / 30
    if L > 30:
        n -= 3 * min(1, (L - 30) / 60)
    if horizonte_bajas > 30:
        n -= 3.5 * min(1, (horizonte_bajas - 30) / 60)
    elif lienzo >= 20 and horizonte_bajas < 15:
        n += 1
    n -= 3 * P / 100
    return max(0.0, min(10.0, n))


# --------------------------------------------------------------- métricas ----
def auc_por_mes(filas: list[dict], clave: str) -> tuple[float, int]:
    """AUC de los días positivos frente a los demás del mismo mes (pares dentro del mes)."""
    favorables = total = 0.0
    por_mes = defaultdict(list)
    for f in filas:
        por_mes[f["mes"]].append(f)
    n_pos = 0
    for grupo in por_mes.values():
        pos = [f[clave] for f in grupo if f["positivo"]]
        neg = [f[clave] for f in grupo if not f["positivo"]]
        n_pos += len(pos)
        for p in pos:
            for q in neg:
                total += 1
                favorables += 1 if p > q else 0.5 if p == q else 0
    return (favorables / total if total else float("nan")), n_pos


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--salida", default="salida/validacion")
    args = a.parse_args()
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    print("[1/3] Días con fotos de amanecer/atardecer en Commons…", flush=True)
    positivos = dias_positivos()
    print(f"  {len(positivos)} días positivos", flush=True)

    print("[2/3] ERA5 en el centro y en el camino del sol…", flush=True)
    centro = era5(*CENTRO, ["cloud_cover_low", "cloud_cover_mid", "cloud_cover_high", "precipitation",
                            "relative_humidity_2m", "wind_speed_10m"])
    caminos: dict[tuple[int, int], pd.DataFrame] = {}
    for az in AZ_ATARDECER + AZ_AMANECER:
        for km in KM_CAMINO:
            la, lo = astro.punto_destino(*CENTRO, az, km)
            caminos[(az, km)] = era5(round(la, 2), round(lo, 2), ["cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"])
            time.sleep(1)
    aq = aire_historico()

    print("[3/3] Notas de cada día…", flush=True)
    filas = []
    d = DESDE
    while d <= HASTA:
        sol = astro.calcular_sol(*CENTRO, d, TZ)
        for momento, hora, signo, azs in (("atardecer", sol.atardecer, 1, AZ_ATARDECER),
                                         ("amanecer", sol.amanecer, -1, AZ_AMANECER)):
            t = hora + timedelta(minutes=15 * signo)
            az = min(azs, key=lambda x: abs(x - (sol.az_atardecer if momento == "atardecer" else sol.az_amanecer)))
            local = en(centro, t)
            if not local:
                continue
            # ERA5 no da probabilidad de lluvia: si llovía (> 0,2 mm/h) la tratamos como segura
            local["precipitation_probability"] = 90 if local.get("precipitation", 0) > 0.2 else 0
            camino = []
            for km in KM_CAMINO:
                c = en(caminos[(az, km)], t)
                camino.append({"km": km, "low": c.get("cloud_cover_low", 0), "mid": c.get("cloud_cover_mid", 0),
                               "high": c.get("cloud_cover_high", 0)})
            ai = en(aq, t)
            lluvia_previa = float(centro.loc[pd.Timestamp((t - timedelta(hours=24)).replace(tzinfo=None)):
                                             pd.Timestamp((t - timedelta(hours=1)).replace(tzinfo=None))]["precipitation"].sum())
            aire = {"aod": None if ai.get("aerosol_optical_depth") is None or math.isnan(ai["aerosol_optical_depth"]) else ai["aerosol_optical_depth"],
                    "polvo": None if ai.get("dust") is None or math.isnan(ai["dust"]) else ai["dust"],
                    "lluvia_previa_mm": lluvia_previa}
            filas.append({
                "fecha": d.isoformat(), "mes": d.month, "momento": momento,
                "positivo": (d.isoformat(), momento) in positivos,
                "fotos": positivos.get((d.isoformat(), momento), 0),
                "v1": nota_luz_v1(local, camino[1]["low"]),
                "v2": nota_luz(local, camino, aire, momento=momento).valor,
                "v2_sin_aire": nota_luz(local, camino, None, momento=momento).valor,
                "v2_sin_camino": nota_luz(local, [], aire, momento=momento).valor,
                "bajas": local.get("cloud_cover_low"), "medias": local.get("cloud_cover_mid"),
                "altas": local.get("cloud_cover_high"), "camino40": camino[1]["low"],
                "aod": aire["aod"], "polvo": aire["polvo"],
            })
        d += timedelta(days=1)
    df = pd.DataFrame(filas)
    df.to_csv(salida / "notas_historicas.csv", index=False)

    lineas = ["# Validación histórica de amanecer y atardecer", "",
              f"Periodo {DESDE}–{HASTA}, centro de Madrid, ERA5. Positivos: días con foto de Commons en la "
              f"ventana de color ({sum(df.positivo)} de {len(df)}).", "",
              "| Momento | Modelo | AUC (mismo mes) | Nota media positivos | Nota media resto | Positivos |",
              "|---|---|---|---|---|---|"]
    resultados = {}
    for momento in ("atardecer", "amanecer", "ambos"):
        sub = df if momento == "ambos" else df[df.momento == momento]
        for clave in ("v1", "v2", "v2_sin_aire", "v2_sin_camino"):
            auc, n = auc_por_mes(sub.to_dict("records"), clave)
            resultados[f"{momento}/{clave}"] = auc
            lineas.append(f"| {momento} | {clave} | {auc:.3f} | {sub[sub.positivo][clave].mean():.2f} | "
                          f"{sub[~sub.positivo][clave].mean():.2f} | {n} |")
    # días de calima fuerte: la nota debería bajar
    if df.polvo.notna().any():
        calima = df[df.polvo > 80]
        lineas += ["", f"Días con polvo > 80 µg/m³: {len(calima)}; nota media v1 {calima.v1.mean():.2f}, "
                       f"v2 {calima.v2.mean():.2f} (resto: v1 {df.v1.mean():.2f}, v2 {df.v2.mean():.2f})."]
    # tasa de acierto por tramos de nota (calibración)
    lineas += ["", "## Calibración v2: % de días fotografiados por tramo de nota", "",
               "| Nota v2 | Días | % con foto |", "|---|---|---|"]
    for lo, hi in ((0, 2), (2, 4), (4, 6), (6, 8), (8, 10.1)):
        t = df[(df.v2 >= lo) & (df.v2 < hi)]
        lineas.append(f"| {lo}-{min(hi, 10):g} | {len(t)} | {100 * t.positivo.mean():.1f} % |")
    # Qué variables separan los días fotografiados (diagnóstico para ajustar, no para sobreajustar)
    lineas += ["", "## Diagnóstico: medias en días con foto frente al resto (mismo momento)", "",
               "| Momento | Variable | Con foto | Resto |", "|---|---|---|---|"]
    for momento in ("atardecer", "amanecer"):
        sub = df[df.momento == momento]
        for v in ("bajas", "medias", "altas", "camino40", "aod", "polvo"):
            lineas.append(f"| {momento} | {v} | {sub[sub.positivo][v].mean():.1f} | {sub[~sub.positivo][v].mean():.1f} |")
    texto = "\n".join(lineas)
    (salida / "validacion.md").write_text(texto)
    (salida / "resultados.json").write_text(json.dumps(resultados, indent=1))
    print(texto)


if __name__ == "__main__":
    main()
