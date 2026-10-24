"""
Validación histórica de las notas de amanecer y atardecer.

¿Separa la nota los días en que el cielo se encendió de los demás? Como "verdad" se usan los días
en que alguien subió a Wikimedia Commons una foto de una puesta o salida de sol en Madrid o
Segovia, hecha en la ventana de color (fecha y hora EXIF). No es una verdad perfecta (también se
fotografían puestas mediocres y muchas buenas no se suben), pero es independiente del modelo.

Para cada día de 2016-2025 se calcula la nota con el tiempo real reanalizado (ERA5, vía el archivo
de Open-Meteo) en el centro de Madrid y en el camino del sol, con el modelo antiguo (v1) y el
nuevo (v2), y se mide el AUC: probabilidad de que un día fotografiado puntúe más que un día
cualquiera **del mismo mes** (0,5 = azar, 1 = perfecto). Se compara por mes para que no gane un
modelo solo por acertar la estación.

Uso: python -m rasante validar [--salida salida/validacion]   (tarda: muchas peticiones a Commons y ERA5)
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import pandas as pd
import requests

from rasante.cielo import astro
from rasante.notas import KM_CAMINO, nota_luz, prob_niebla_radiacion

from .fuentes import (
    AEROPUERTOS,
    AZ_AMANECER,
    AZ_ATARDECER,
    CENTRO,
    DESDE,
    HASTA,
    TZ,
    aire_historico,
    dias_positivos,
    en,
    era5,
    metar,
)
from .modelos_v1 import niebla_v1, nota_luz_v1


def validar_niebla() -> list[str]:
    filas = []
    for est, (lat, lon) in AEROPUERTOS.items():
        try:
            obs = metar(est)
            met = era5(
                lat,
                lon,
                [
                    "temperature_2m",
                    "dew_point_2m",
                    "relative_humidity_2m",
                    "wind_speed_10m",
                    "cloud_cover",
                    "precipitation",
                ],
            )
        except (requests.RequestException, RuntimeError, ValueError) as e:
            print(f"  {est}: sin datos ({e})", flush=True)
            continue
        print(f"  {est}: {len(obs)} METAR", flush=True)
        d = DESDE
        while d <= HASTA:
            sol = astro.calcular_sol(lat, lon, d, TZ)
            if sol.amanecer:
                a = pd.Timestamp((sol.amanecer - timedelta(hours=3)).replace(tzinfo=None))
                b = pd.Timestamp((sol.amanecer + timedelta(hours=1)).replace(tzinfo=None))
                o = obs.loc[a:b]
                if len(o) >= 3:
                    wx = o["wxcodes"].fillna("").astype(str)
                    hay = bool(wx.str.contains(r"FG").any() or (pd.to_numeric(o["vsby"], errors="coerce") < 0.62).any())
                    madrugada = met.loc[a:b].to_dict("records")
                    noche = met.loc[a - pd.Timedelta(hours=6) : a].to_dict("records")
                    lluvia = float(met.loc[a - pd.Timedelta(hours=33) : b]["precipitation"].sum())
                    p2, _ = prob_niebla_radiacion(madrugada)
                    p1 = max((niebla_v1(f) for f in madrugada), default=0.0)
                    hm = met.loc[a:b]
                    dpd = hm["temperature_2m"] - hm["dew_point_2m"]
                    i = dpd.idxmin() if not dpd.empty and dpd.notna().any() else None
                    filas.append(
                        {
                            "estacion": est,
                            "fecha": d.isoformat(),
                            "mes": d.month,
                            "positivo": hay,
                            "v1": p1,
                            "v2": p2,
                            # variables en bruto para ajustar el modelo fuera de línea
                            "rh_max": float(hm["relative_humidity_2m"].max()) if not hm.empty else None,
                            "dpd_min": float(dpd.min()) if i is not None else None,
                            "viento_en_dpd_min": float(hm.loc[i, "wind_speed_10m"]) if i is not None else None,
                            "viento_min": float(hm["wind_speed_10m"].min()) if not hm.empty else None,
                            "nubes_noche": float(pd.DataFrame(noche)["cloud_cover"].mean()) if noche else None,
                            "lluvia_36h": lluvia,
                        }
                    )
            d += timedelta(days=1)
    if not filas:
        return ["", "## Niebla: sin datos METAR"]
    df = pd.DataFrame(filas)
    lineas = [
        "",
        "## Niebla al amanecer frente a METAR (FG o visibilidad < 1 km)",
        "",
        f"{len(df)} madrugadas en {df.estacion.nunique()} aeropuertos, {int(df.positivo.sum())} con niebla "
        f"({100 * df.positivo.mean():.1f} %).",
        "",
        "| Modelo | AUC global | AUC mismo mes | Prob. media con niebla | Sin niebla |",
        "|---|---|---|---|---|",
    ]
    for clave in ("v1", "v2"):
        glob = auc_por_mes([{**f, "mes": 0} for f in filas], clave)[0]
        mes = auc_por_mes(filas, clave)[0]
        lineas.append(
            f"| {clave} | {glob:.3f} | {mes:.3f} | {df[df.positivo][clave].mean():.2f} | "
            f"{df[~df.positivo][clave].mean():.2f} |"
        )
    lineas += ["", "| Prob. v2 | Madrugadas | % con niebla |", "|---|---|---|"]
    for lo, hi in ((0, 0.1), (0.1, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 1.01)):
        t = df[(df.v2 >= lo) & (df.v2 < hi)]
        lineas.append(f"| {lo:.1f}-{min(hi, 1):.1f} | {len(t)} | {100 * t.positivo.mean():.1f} % |")
    df.to_csv(Path("salida/validacion") / "niebla_historica.csv", index=False)
    return lineas


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


def main(argv: list[str] | None = None) -> None:
    a = argparse.ArgumentParser(
        prog="python -m rasante validar", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    a.add_argument("--salida", default="salida/validacion")
    args = a.parse_args(argv)
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    print("[1/3] Días con fotos de amanecer/atardecer en Commons…", flush=True)
    positivos = dias_positivos()
    print(f"  {len(positivos)} días positivos", flush=True)

    print("[2/3] ERA5 en el centro y en el camino del sol…", flush=True)
    centro = era5(
        *CENTRO,
        [
            "cloud_cover_low",
            "cloud_cover_mid",
            "cloud_cover_high",
            "precipitation",
            "relative_humidity_2m",
            "wind_speed_10m",
        ],
    )
    caminos: dict[tuple[int, int], pd.DataFrame] = {}
    for az in AZ_ATARDECER + AZ_AMANECER:
        for km in KM_CAMINO:
            la, lo = astro.punto_destino(*CENTRO, az, km)
            caminos[(az, km)] = era5(
                round(la, 2), round(lo, 2), ["cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"]
            )
            time.sleep(1)
    aq = aire_historico()

    print("[3/3] Notas de cada día…", flush=True)
    filas = []
    d = DESDE
    while d <= HASTA:
        sol = astro.calcular_sol(*CENTRO, d, TZ)
        for momento, hora, signo, azs in (
            ("atardecer", sol.atardecer, 1, AZ_ATARDECER),
            ("amanecer", sol.amanecer, -1, AZ_AMANECER),
        ):
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
                camino.append(
                    {
                        "km": km,
                        "low": c.get("cloud_cover_low", 0),
                        "mid": c.get("cloud_cover_mid", 0),
                        "high": c.get("cloud_cover_high", 0),
                    }
                )
            ai = en(aq, t)
            lluvia_previa = float(
                centro.loc[
                    pd.Timestamp((t - timedelta(hours=24)).replace(tzinfo=None)) : pd.Timestamp(
                        (t - timedelta(hours=1)).replace(tzinfo=None)
                    )
                ]["precipitation"].sum()
            )
            aire = {
                "aod": None
                if ai.get("aerosol_optical_depth") is None or math.isnan(ai["aerosol_optical_depth"])
                else ai["aerosol_optical_depth"],
                "polvo": None if ai.get("dust") is None or math.isnan(ai["dust"]) else ai["dust"],
                "lluvia_previa_mm": lluvia_previa,
            }
            filas.append(
                {
                    "fecha": d.isoformat(),
                    "mes": d.month,
                    "momento": momento,
                    "positivo": (d.isoformat(), momento) in positivos,
                    "fotos": positivos.get((d.isoformat(), momento), 0),
                    "v1": nota_luz_v1(local, camino[1]["low"]),
                    "v2": nota_luz(local, camino, aire, momento=momento).valor,
                    "v2_sin_aire": nota_luz(local, camino, None, momento=momento).valor,
                    "v2_medias06": nota_luz(local, camino, aire, momento=momento, peso_medias=0.6).valor,
                    "v2_medias04": nota_luz(local, camino, aire, momento=momento, peso_medias=0.4).valor,
                    "v2_sin_camino": nota_luz(local, [], aire, momento=momento).valor,
                    "bajas": local.get("cloud_cover_low"),
                    "medias": local.get("cloud_cover_mid"),
                    "altas": local.get("cloud_cover_high"),
                    "camino40": camino[1]["low"],
                    "humedad": local.get("relative_humidity_2m"),
                    "lluvia": local.get("precipitation"),
                    "lluvia_previa": lluvia_previa,
                    **{f"c{p['km']}_{k}": p[k] for p in camino for k in ("low", "mid", "high")},
                    "aod": aire["aod"],
                    "polvo": aire["polvo"],
                }
            )
        d += timedelta(days=1)
    df = pd.DataFrame(filas)
    df.to_csv(salida / "notas_historicas.csv", index=False)

    lineas = [
        "# Validación histórica de amanecer y atardecer",
        "",
        f"Periodo {DESDE}–{HASTA}, centro de Madrid, ERA5. Positivos: días con foto de Commons en la "
        f"ventana de color ({sum(df.positivo)} de {len(df)}).",
        "",
        "| Momento | Modelo | AUC (mismo mes) | Nota media positivos | Nota media resto | Positivos |",
        "|---|---|---|---|---|---|",
    ]
    resultados = {}
    for momento in ("atardecer", "amanecer", "ambos"):
        sub = df if momento == "ambos" else df[df.momento == momento]
        for clave in ("v1", "v2", "v2_sin_aire", "v2_sin_camino", "v2_medias06", "v2_medias04"):
            auc, n = auc_por_mes(sub.to_dict("records"), clave)
            resultados[f"{momento}/{clave}"] = auc
            lineas.append(
                f"| {momento} | {clave} | {auc:.3f} | {sub[sub.positivo][clave].mean():.2f} | "
                f"{sub[~sub.positivo][clave].mean():.2f} | {n} |"
            )
    # días de calima fuerte: la nota debería bajar
    if df.polvo.notna().any():
        calima = df[df.polvo > 80]
        lineas += [
            "",
            f"Días con polvo > 80 µg/m³: {len(calima)}; nota media v1 {calima.v1.mean():.2f}, "
            f"v2 {calima.v2.mean():.2f} (resto: v1 {df.v1.mean():.2f}, v2 {df.v2.mean():.2f}).",
        ]
    # tasa de acierto por tramos de nota (calibración)
    lineas += [
        "",
        "## Calibración v2: % de días fotografiados por tramo de nota",
        "",
        "| Nota v2 | Días | % con foto |",
        "|---|---|---|",
    ]
    for lo, hi in ((0, 2), (2, 4), (4, 6), (6, 8), (8, 10.1)):
        t = df[(df.v2 >= lo) & (df.v2 < hi)]
        lineas.append(f"| {lo}-{min(hi, 10):g} | {len(t)} | {100 * t.positivo.mean():.1f} % |")
    # Qué variables separan los días fotografiados (diagnóstico para ajustar, no para sobreajustar)
    lineas += [
        "",
        "## Diagnóstico: medias en días con foto frente al resto (mismo momento)",
        "",
        "| Momento | Variable | Con foto | Resto |",
        "|---|---|---|---|",
    ]
    for momento in ("atardecer", "amanecer"):
        sub = df[df.momento == momento]
        for v in ("bajas", "medias", "altas", "camino40", "aod", "polvo"):
            lineas.append(
                f"| {momento} | {v} | {sub[sub.positivo][v].mean():.1f} | {sub[~sub.positivo][v].mean():.1f} |"
            )
    print("[4/4] Niebla frente a METAR de los aeropuertos de Madrid…", flush=True)
    lineas += validar_niebla()
    texto = "\n".join(lineas)
    (salida / "validacion.md").write_text(texto)
    (salida / "resultados.json").write_text(json.dumps(resultados, indent=1))
    print(texto)
