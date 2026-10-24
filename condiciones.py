#!/usr/bin/env python3
"""
condiciones.py — Condiciones y nota diaria (0-10) de cada spot para foto de paisaje y nocturna.

Lee los spots (spots.geojson de descubrir_spots.py y mis_spots.csv con los tuyos), pide la
previsión a Open-Meteo y calcula sol, luna y Vía Láctea (astro.py). Para cada spot y día:

  - amanecer / atardecer (modelo de camino de la luz, puntuacion.nota_luz): nubes por capas en el
    spot en el pico de color (15 min antes de salir / después de ponerse el sol, interpolado),
    nubes bajas a 15/40/80/150 km hacia el sol, aerosoles y polvo (CAMS), humedad y lluvia previa.
  - noche (puntuacion.nota_astro): calidad hora a hora y mejor ventana de 3 h, transparencia
    (vapor de agua, aerosoles), contaminación lumínica local y cúpula de luz hacia el núcleo de la
    Vía Láctea o el sur.
  - niebla (puntuacion.nota_niebla): niebla de radiación y mar de nubes con el perfil vertical
    (niveles de presión) en el llano.
  - confianza: la misma nota con las nubes de un segundo modelo (ECMWF IFS); si no coinciden, la
    previsión es dudosa aunque la nota sea alta.

Uso:
  python condiciones.py                                   # 5 días → public/datos/informe.json
  python condiciones.py --dias 3 --spots public/datos/spots.geojson --mis-spots mis_spots.csv

mis_spots.csv (opcional): nombre,lat,lon[,tipo]   (las líneas que empiezan por # se ignoran)
Open-Meteo es gratuito y sin clave para uso no comercial (también su API de calidad del aire, CAMS).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

import astro
from comun import USER_AGENT, ccaa_de, escribir_json, id_spot
from contaminacion import contaminacion, cupula
import horizonte as hzmod
from puntuacion import KM_CAMINO, _v, capa_nubosa, nota_astro, nota_luna, nota_luz, nota_niebla

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
AIRE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
# Open-Meteo cuenta 1 llamada por punto hasta 10 variables (gratis: 10 000 al día, 600 al minuto):
# en el spot se piden exactamente 10 y se derivan la nubosidad total y el punto de rocío.
VARS_SPOT = [
    "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high", "visibility", "precipitation_probability",
    "precipitation", "wind_speed_10m", "wind_gusts_10m", "relative_humidity_2m", "temperature_2m",
]
VARS_CAMINO = ["cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"]
NIVELES_HPA = (1000, 975, 950, 925, 900, 850, 800, 700)
VARS_PERFIL = [f"{v}_{p}hPa" for p in NIVELES_HPA
               for v in ("temperature", "relative_humidity", "cloud_cover", "geopotential_height")] + [
    "total_column_integrated_water_vapour"]
VARS_ALT = ["cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"]
MODELO_ALT = "ecmwf_ifs025"
# Rejillas (grados) para compartir peticiones entre spots: lejos del spot basta una rejilla gruesa
REDONDEO_SPOT = 0.05
REDONDEO_CAMINO = {15: 0.1, 40: 0.25, 80: 0.25, 150: 0.5}
REDONDEO_PERFIL = 0.5
REDONDEO_ALT = 0.25     # ECMWF IFS tiene 0,25° de resolución: más fino no aporta
KM_PERFIL = 40          # el perfil vertical se toma en el llano, en los puntos a 40 km
LLAMADAS_POR_MINUTO = 450
MIN_PICO = 15           # el color es máximo ~15 min antes de salir el sol / después de ponerse
LOTE_COORDS = 100
DIAS_POR_DEFECTO = 5
TIPOS_AGUA = {"lago", "embalse", "playa", "cascada", "río", "costa"}
CACHE = Path("cache")


def fiabilidad(indice_dia: int) -> str:
    """La nubosidad prevista pierde mucha precisión a partir del tercer día."""
    return "alta" if indice_dia <= 1 else "media" if indice_dia == 2 else "baja"


def _hhmm(t: datetime | None) -> str | None:
    return t.strftime("%H:%M") if t else None


def _tramo(par) -> list[str] | None:
    return [_hhmm(par[0]), _hhmm(par[1])] if par else None


def _r(x, n=0):
    if x is None:
        return None
    return round(x, n) if n else int(round(x))


def _redondear(c: tuple[float, float], paso: float) -> tuple[float, float]:
    return (round(round(c[0] / paso) * paso, 4), round(round(c[1] / paso) * paso, 4))


# ---------------------------------------------------------------- spots ----
def cargar_spots(geojson: Path | None, csv: Path | None) -> list[dict]:
    spots: list[dict] = []
    if geojson and geojson.exists():
        for f in json.loads(geojson.read_text())["features"]:
            p = f["properties"]
            lon, lat = f["geometry"]["coordinates"]
            nombre = p.get("nombre") or f"Spot {p.get('spot_id')}"
            spots.append({"id": p.get("id") or id_spot(nombre, lat, lon), "nombre": nombre,
                          "lat": lat, "lon": lon, "tipo": p.get("tipo_osm"),
                          "origen": p.get("origen") or "commons",
                          "contaminacion": p.get("contaminacion"), "relieve": p.get("horizonte"),
                          "provincia": p.get("provincia"), "ccaa": ccaa_de(p.get("provincia"), p.get("ccaa"))})
    if csv and csv.exists():
        df = pd.read_csv(csv, comment="#", skip_blank_lines=True)
        for r in df.itertuples():
            tipo = getattr(r, "tipo", None)
            spots.append({"id": id_spot(r.nombre, float(r.lat), float(r.lon)), "nombre": r.nombre,
                          "lat": float(r.lat), "lon": float(r.lon),
                          "tipo": tipo if isinstance(tipo, str) else None,
                          "origen": "propio", "contaminacion": None, "relieve": None})
    if not spots:
        raise SystemExit("No hay spots: ejecuta descubrir_spots.py o añade alguno a mis_spots.csv")
    vistos, unicos = set(), []
    for s in spots:
        if s["id"] not in vistos:
            vistos.add(s["id"])
            unicos.append(s)
    return unicos


# ------------------------------------------------------------ peticiones ----
def _cache_get(clave, max_edad_s=2 * 3600):
    f = CACHE / f"om_{hashlib.sha1(clave.encode()).hexdigest()}.json"
    if f.exists() and time.time() - f.stat().st_mtime < max_edad_s:
        return json.loads(f.read_text())
    return None


def _cache_set(clave, datos):
    CACHE.mkdir(exist_ok=True)
    (CACHE / f"om_{hashlib.sha1(clave.encode()).hexdigest()}.json").write_text(json.dumps(datos))


def _get(url: str, params: dict, obligatorio: bool = True):
    clave = url + json.dumps(params, sort_keys=True)
    datos = _cache_get(clave)
    if datos is not None:
        return datos
    for intento in range(5):
        try:
            r = requests.get(url, params=params, timeout=90, headers={"User-Agent": USER_AGENT})
        except requests.RequestException as e:   # cortes de conexión puntuales
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
        except ValueError:   # a veces responde 200 con el cuerpo vacío o cortado: se reintenta
            print(f"  {url.split('/')[2]}: respuesta no JSON, reintento")
            time.sleep(10 * (intento + 1))
            continue
        _cache_set(clave, datos)
        return datos
    if obligatorio:
        raise SystemExit(f"{url} no responde")
    return None


def pedir(coords: list[tuple[float, float]], variables: list[str], dias: int, tz_nombre: str,
          url: str = OPEN_METEO_URL, extra: dict | None = None, obligatorio: bool = True) -> list[dict | None]:
    """Serie horaria para una lista de (lat, lon). Por coordenada: {"elevacion", "horas": DataFrame
    indexado por hora local (naive)}, o None si una API opcional no respondió."""
    out: list[dict | None] = []
    peso = max(1.0, len(variables) / 10)
    for i in range(0, len(coords), LOTE_COORDS):
        lote = coords[i:i + LOTE_COORDS]
        _ritmo(len(lote) * peso)
        params = {"latitude": ",".join(str(c[0]) for c in lote),
                  "longitude": ",".join(str(c[1]) for c in lote),
                  "hourly": ",".join(variables), "timezone": tz_nombre,
                  "forecast_days": min(dias + 1, 16), **(extra or {})}
        datos = _get(url, params, obligatorio)
        if datos is None:
            out += [None] * len(lote)
            continue
        if isinstance(datos, dict):      # una sola coordenada → objeto, varias → lista
            datos = [datos]
        for d in datos:
            out.append(_a_tabla(d))
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


def _a_tabla(d: dict) -> dict:
    df = pd.DataFrame(d["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").apply(pd.to_numeric, errors="coerce")
    # con models=… las columnas llevan el nombre del modelo como sufijo: se quita
    df.columns = [c.removesuffix(f"_{MODELO_ALT}") for c in df.columns]
    return {"elevacion": d.get("elevation"), "horas": _derivar(df)}


def _derivar(df: pd.DataFrame) -> pd.DataFrame:
    """Variables que no se piden para no pasar de 10 por punto."""
    if "cloud_cover" not in df and {"cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"} <= set(df):
        capas = df[["cloud_cover_low", "cloud_cover_mid", "cloud_cover_high"]].fillna(0) / 100
        maximo = capas.max(axis=1)
        aleatorio = 1 - (1 - capas).prod(axis=1)
        # entre solapamiento máximo y aleatorio, como hacen los modelos
        df["cloud_cover"] = 100 * (maximo + aleatorio) / 2
    if "dew_point_2m" not in df and {"temperature_2m", "relative_humidity_2m"} <= set(df):
        t, hr = df["temperature_2m"], df["relative_humidity_2m"].clip(lower=1)
        g = np.log(hr / 100) + 17.625 * t / (243.04 + t)       # Magnus
        df["dew_point_2m"] = 243.04 * g / (17.625 - g)
    return df


# ---------------------------------------------------------- interpolación ----
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
    return {k: (a[k] if pd.isna(b[k]) else b[k] if pd.isna(a[k]) else a[k] + (b[k] - a[k]) * w)
            for k in df.columns}


def filas_entre(df: pd.DataFrame, ini: datetime, fin: datetime) -> pd.DataFrame:
    return df.loc[pd.Timestamp(ini.replace(tzinfo=None)):pd.Timestamp(fin.replace(tzinfo=None))]


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
        niveles.append({"hpa": p, "z": float(z), "t": f.get(f"temperature_{p}hPa"),
                        "hr": f.get(f"relative_humidity_{p}hPa"), "nubes": f.get(f"cloud_cover_{p}hPa")})
    return {"niveles": sorted(niveles, key=lambda x: x["z"])}


def _meteo_momento(f: dict, camino: list[dict], aire: dict) -> dict:
    return {"nubes_bajas": _r(_v(f, "cloud_cover_low")), "nubes_medias": _r(_v(f, "cloud_cover_mid")),
            "nubes_altas": _r(_v(f, "cloud_cover_high")),
            "nubes_horizonte": _r(max((_v(p, "low") for p in camino), default=0)),
            "camino": [{"km": p["km"], "bajas": _r(_v(p, "low"))} for p in camino],
            "visibilidad_km": _r(_v(f, "visibility", 24000) / 1000, 1),
            "lluvia": _r(_v(f, "precipitation_probability")), "viento": _r(_v(f, "wind_speed_10m")),
            "temperatura": _r(_v(f, "temperature_2m"), 1), "humedad": _r(_v(f, "relative_humidity_2m")),
            "aod": aire.get("aod"), "polvo": aire.get("polvo")}


def _confianza(nota: float, alternativa: float | None) -> str | None:
    if alternativa is None:
        return None
    d = abs(nota - alternativa)
    return "alta" if d < 1.5 else "media" if d < 3 else "baja"


def _aire_en(aq: pd.DataFrame | None, t: datetime) -> dict:
    f = en(aq, t)
    aod, polvo = f.get("aerosol_optical_depth"), f.get("dust")
    return {"aod": None if aod is None or pd.isna(aod) else round(float(aod), 2),
            "polvo": None if polvo is None or pd.isna(polvo) else round(float(polvo))}


# ------------------------------------------------------------- evaluación ----
def evaluar_spot_dia(spot: dict, dia: date, indice: int, tz: ZoneInfo, datos: dict) -> dict:
    """datos: {"spot": df, "elevacion", "camino": {momento: [(km, df)]}, "perfil": [(df, elevación)],
    "alt": df, "aire": df}."""
    df, alt, aq = datos["spot"], datos.get("alt"), datos.get("aire")
    perfil_relieve = spot.get("relieve")
    hz = (lambda az: hzmod.angulo(perfil_relieve, az) or 0.0) if perfil_relieve else None
    sol = astro.calcular_sol(spot["lat"], spot["lon"], dia, tz)
    noche = astro.calcular_noche(spot["lat"], spot["lon"], dia, tz, sol, horizonte=hz)
    relieve = {}
    if hz:
        for m in ("amanecer", "atardecer"):
            hora_r, ang = astro.sol_sobre_relieve(spot["lat"], spot["lon"], dia, tz, hz, m)
            relieve[m] = (hora_r, ang)
    es_agua = (spot.get("tipo") or "") in TIPOS_AGUA
    notas, meteo, avisos = {}, {}, []

    # ---- amanecer y atardecer, en el pico de color
    for momento, hora, signo in (("amanecer", sol.amanecer, -1), ("atardecer", sol.atardecer, 1)):
        if hora is None:
            continue
        t = hora + timedelta(minutes=signo * MIN_PICO)
        f = en(df, t)
        camino = []
        for km, h in datos["camino"].get(momento, []):
            fc = en(h, t)
            camino.append({"km": km, "low": _v(fc, "cloud_cover_low"), "mid": _v(fc, "cloud_cover_mid"),
                           "high": _v(fc, "cloud_cover_high")})
        aire = _aire_en(aq, t)
        aire["lluvia_previa_mm"] = suma_entre(df, "precipitation", t - timedelta(hours=24), t - timedelta(hours=1))
        h_rel, ang_rel = relieve.get(momento, (None, None))
        kw_rel = {"relieve": ang_rel, "hora_relieve": _hhmm(h_rel)}
        n = nota_luz(f, camino, aire, es_agua=es_agua, momento=momento, **kw_rel)
        d = n.a_dict()
        if alt is not None:
            fa = {**f, **{k: v for k, v in en(alt, t).items() if k in VARS_ALT}}
            d["confianza"] = _confianza(n.valor, nota_luz(fa, camino, aire, es_agua, momento, **kw_rel).valor)
        notas[momento] = d
        meteo[momento] = _meteo_momento(f, camino, aire)

    # ---- noche
    lp = spot.get("contaminacion") or {}
    if noche.ini and noche.fin:
        horas, horas_alt = [], []
        t = noche.ini
        while t < noche.fin:
            luna = noche.luna_iluminacion if astro.altura_luna(spot["lat"], spot["lon"], t) > 0 else 0.0
            horas.append({"t": _hhmm(t), "nubes": _v(en(df, t), "cloud_cover", 100), "luna": luna})
            if alt is not None:
                horas_alt.append({"t": _hhmm(t), "nubes": _v(en(alt, t), "cloud_cover", 100), "luna": luna})
            t += timedelta(hours=1)
        toda = filas_entre(df, noche.ini, noche.fin)
        margen = float((toda["temperature_2m"] - toda["dew_point_2m"]).min()) if not toda.empty else 99.0
        mitad = noche.ini + (noche.fin - noche.ini) / 2
        aire_noche = _aire_en(aq, mitad)
        hacia_nucleo = noche.vl_azimut_max is not None
        try:
            cup = cupula(spot["lat"], spot["lon"], noche.vl_azimut_max if hacia_nucleo else 180.0)
        except requests.RequestException:
            cup = None
        if cup:
            cup["hacia"] = "el núcleo de la Vía Láctea" if hacia_nucleo else "el sur"
        perfiles = [p for p, _ in datos.get("perfil", []) if p is not None]
        vapor = en(perfiles[0], mitad).get("total_column_integrated_water_vapour") if perfiles else None
        args = dict(sqm=lp.get("sqm"), zona_lp=lp.get("zona"), cupula=cup,
                    vapor_mm=None if vapor is None or pd.isna(vapor) else float(vapor),
                    aod=aire_noche["aod"], elevacion=datos.get("elevacion"),
                    vl_horas_sin_luna=noche.vl_horas_sin_luna, vl_altura_max=noche.vl_altura_max,
                    margen_rocio=margen,
                    rachas=float(toda["wind_gusts_10m"].max()) if not toda.empty else 0.0,
                    humedad=float(toda["relative_humidity_2m"].mean()) if not toda.empty else 60.0)
        n = nota_astro(horas, **args)
        d = n.a_dict()
        if horas_alt:
            d["confianza"] = _confianza(n.valor, nota_astro(horas_alt, **args).valor)
        notas["astro"] = d
        meteo["noche"] = {
            "nubes": _r(sum(h["nubes"] for h in horas) / len(horas)) if horas else None,
            "humedad": _r(args["humedad"]),
            "viento": _r(float(toda["wind_speed_10m"].mean())) if not toda.empty else None,
            "rachas": _r(args["rachas"]),
            "temp_min": _r(float(toda["temperature_2m"].min()), 1) if not toda.empty else None,
            "punto_rocio": _r(float(toda["dew_point_2m"].max()), 1) if not toda.empty else None,
            "margen_rocio": _r(margen, 1), "vapor_mm": _r(args["vapor_mm"]),
            "aod": aire_noche["aod"], "cupula": cup,
            "horas": [{"t": h["t"], "nubes": _r(h["nubes"]), "luna": round(h["luna"], 2)} for h in horas],
        }
    else:
        notas["astro"] = nota_astro([], None).a_dict()

    # ---- luna sobre el paisaje en el crepúsculo
    ev = astro.evento_luna(spot["lat"], spot["lon"], dia, tz, sol, hz)
    evento = None
    if ev:
        evento = {"tipo": ev.tipo, "hora": _hhmm(ev.hora), "azimut": round(ev.azimut), "horizonte": round(ev.horizonte, 1),
                  "iluminacion": round(ev.iluminacion, 2), "altura_sol": round(ev.altura_sol, 1)}
        lado = "amanecer" if ev.tipo == "salida" else "atardecer"   # la luna llena sale por el este y se pone por el oeste
        cam_luna = [{"km": km, "low": _v(en(h, ev.hora), "cloud_cover_low")} for km, h in datos["camino"].get(lado, [])]
        notas["luna"] = nota_luna(evento, en(df, ev.hora), cam_luna).a_dict()
        if alt is not None:
            fa = {**en(df, ev.hora), **{k: v for k, v in en(alt, ev.hora).items() if k in VARS_ALT}}
            notas["luna"]["confianza"] = _confianza(notas["luna"]["nota"], nota_luna(evento, fa, cam_luna).valor)
    else:
        notas["luna"] = nota_luna(None).a_dict()

    # ---- niebla y mar de nubes, al amanecer
    if sol.amanecer:
        madrugada = filas_entre(df, sol.amanecer - timedelta(hours=3), sol.amanecer + timedelta(hours=1))
        capas = [c for c in (capa_nubosa(perfil_en(p, sol.amanecer, suelo))
                             for p, suelo in datos.get("perfil", [])) if c]
        capa = max(capas, key=lambda c: c["cobertura"]) if capas else None
        n = nota_niebla(madrugada.to_dict("records"), datos.get("elevacion"), capa, spot.get("tipo"),
                        _v(en(df, sol.amanecer), "cloud_cover_low"))
        notas["niebla"] = n.a_dict()
        if capa:
            meteo["capa_nubosa"] = {"techo": _r(capa["techo"]), "cobertura": _r(capa["cobertura"]),
                                    "inversion": _r(capa["inversion"], 1)}

    for n in notas.values():
        avisos += [a for a in n["avisos"] if a not in avisos]

    return {
        "fecha": dia.isoformat(), "fiabilidad": fiabilidad(indice),
        "sol": {"amanecer": _hhmm(sol.amanecer), "atardecer": _hhmm(sol.atardecer),
                "amanecer_relieve": _hhmm(relieve.get("amanecer", (None,))[0]),
                "atardecer_relieve": _hhmm(relieve.get("atardecer", (None,))[0]),
                "relieve_amanecer": _r(relieve.get("amanecer", (None, None))[1], 1),
                "relieve_atardecer": _r(relieve.get("atardecer", (None, None))[1], 1),
                "az_amanecer": _r(sol.az_amanecer), "az_atardecer": _r(sol.az_atardecer),
                "dorada_manana": _tramo(sol.dorada_manana), "dorada_tarde": _tramo(sol.dorada_tarde),
                "azul_manana": _tramo(sol.azul_manana), "azul_tarde": _tramo(sol.azul_tarde)},
        "noche": {
            "ini": _hhmm(noche.ini), "fin": _hhmm(noche.fin), "horas": _r(noche.horas_oscuras, 1),
            "luna": {"fase": noche.luna_fase, "iluminacion": _r(noche.luna_iluminacion * 100),
                     "edad": _r(noche.luna_edad, 1), "salida": _hhmm(noche.luna_salida),
                     "puesta": _hhmm(noche.luna_puesta),
                     "sin_luna": [_tramo(t) for t in noche.sin_luna], "evento": evento,
                     "horas_sin_luna": _r(noche.horas_sin_luna, 1)},
            "via_lactea": {"tramos": [_tramo(t) for t in noche.vl_tramos], "horas": _r(noche.vl_horas, 1),
                           "horas_sin_luna": _r(noche.vl_horas_sin_luna, 1),
                           "altura_max": _r(noche.vl_altura_max), "azimut_max": _r(noche.vl_azimut_max),
                           "hora_max": _hhmm(noche.vl_hora_max),
                           "azimut_ini": _r(noche.vl_azimut_ini), "azimut_fin": _r(noche.vl_azimut_fin)},
        },
        "meteo": meteo, "notas": notas, "avisos": avisos,
    }


def planificar(spots: list[dict], dia0: date, tz: ZoneInfo) -> tuple[dict, list[dict]]:
    """Qué puntos pedir y a qué spot sirve cada uno. El azimut del sol cambia menos de 1° al día:
    se usa el del primer día para todo el informe."""
    puntos: dict[str, dict[tuple[float, float], int]] = {"spot": {}, "camino": {}, "perfil": {}, "alt": {}}

    def indice(tipo, c):
        return puntos[tipo].setdefault(c, len(puntos[tipo]))

    planes = []
    for s in spots:
        sol0 = astro.calcular_sol(s["lat"], s["lon"], dia0, tz)
        plan = {"spot": indice("spot", _redondear((s["lat"], s["lon"]), REDONDEO_SPOT)), "camino": {},
                "perfil": [], "horizonte": {},
                "alt": indice("alt", _redondear((s["lat"], s["lon"]), REDONDEO_ALT))}
        for momento, az in (("amanecer", sol0.az_amanecer), ("atardecer", sol0.az_atardecer)):
            if az is None:
                continue
            plan["camino"][momento] = []
            for km in KM_CAMINO:
                c = _redondear(astro.punto_destino(s["lat"], s["lon"], az, km), REDONDEO_CAMINO[km])
                plan["camino"][momento].append((km, indice("camino", c)))
                if km == KM_PERFIL:
                    plan["perfil"].append(indice("perfil", _redondear(c, REDONDEO_PERFIL)))
                    plan["horizonte"][momento] = list(c)
        planes.append(plan)
    return puntos, planes


def pedir_todo(puntos: dict, dias: int, tz_nombre: str) -> dict:
    c_spot, c_camino, c_perfil, c_alt = (list(puntos[k]) for k in ("spot", "camino", "perfil", "alt"))
    print(f"  Open-Meteo: {len(c_spot)} celdas de spots, {len(c_camino)} puntos del camino del sol, "
          f"{len(c_perfil)} perfiles verticales, {len(c_alt)} celdas del segundo modelo")
    prev = {
        "spot": pedir(c_spot, VARS_SPOT, dias, tz_nombre, extra={"past_days": 2}),
        "camino": pedir(c_camino, VARS_CAMINO, dias, tz_nombre),
        "perfil": pedir(c_perfil, VARS_PERFIL, dias, tz_nombre),
        "alt": pedir(c_alt, VARS_ALT, dias, tz_nombre, extra={"models": MODELO_ALT}, obligatorio=False),
    }
    # Aerosoles y polvo (CAMS): rejilla de 0,4°, basta un punto por celda
    celdas = sorted({_redondear(c, 0.4) for c in c_spot})
    aire = pedir(celdas, ["aerosol_optical_depth", "dust"], min(dias, 4), tz_nombre, url=AIRE_URL,
                 obligatorio=False)
    por_celda = dict(zip(celdas, aire))
    prev["aire"] = [por_celda.get(_redondear(c, 0.4)) for c in c_spot]
    print(f"  ≈ {LLAMADAS['total']:.0f} llamadas a Open-Meteo en esta ejecución")
    return prev


def evaluar(spots: list[dict], dias: int, tz_nombre: str, hoy: date | None = None,
            previsiones: dict | None = None) -> dict:
    """previsiones (para tests): {"spot": [...], "camino": [...], "perfil": [...], "alt": [...],
    "aire": [...]} con el formato de pedir(), en el orden de planificar()."""
    tz = ZoneInfo(tz_nombre)
    hoy = hoy or datetime.now(tz).date()
    fechas = [hoy + timedelta(days=i) for i in range(dias)]

    for s in spots:
        if s.get("contaminacion") is None:
            try:
                s["contaminacion"] = contaminacion(s["lat"], s["lon"])
            except requests.RequestException as e:
                print(f"  sin atlas de contaminación para {s['nombre']}: {e}")

    puntos, planes = planificar(spots, fechas[0], tz)
    if previsiones is None:
        previsiones = pedir_todo(puntos, dias, tz_nombre)

    def horas(lista, i):
        x = lista[i] if lista and i < len(lista) else None
        return x["horas"] if x else None

    salida = []
    for s, plan in zip(spots, planes):
        p = previsiones["spot"][plan["spot"]]
        datos = {"spot": p["horas"], "elevacion": p["elevacion"],
                 "camino": {m: [(km, horas(previsiones["camino"], i)) for km, i in pts]
                            for m, pts in plan["camino"].items()},
                 "perfil": [(horas(previsiones["perfil"], i), (previsiones["perfil"][i] or {}).get("elevacion"))
                            for i in plan["perfil"]],
                 "alt": horas(previsiones.get("alt"), plan["alt"]),
                 "aire": horas(previsiones.get("aire"), plan["spot"])}
        dias_spot = [evaluar_spot_dia(s, d, i, tz, datos) for i, d in enumerate(fechas)]
        salida.append({
            "id": s["id"], "nombre": s["nombre"], "lat": round(s["lat"], 5), "lon": round(s["lon"], 5),
            "tipo": s.get("tipo"), "origen": s.get("origen"),
            "elevacion": _r((s.get("relieve") or {}).get("elevacion") or p["elevacion"]),
            "provincia": s.get("provincia"), "ccaa": s.get("ccaa"),
            "contaminacion": s.get("contaminacion"), "horizonte": plan["horizonte"],
            "dias": dias_spot,
        })
    return {
        "generado": datetime.now(tz).isoformat(timespec="minutes"),
        "zona_horaria": tz_nombre,
        "modelo": "v2",
        "fechas": [f.isoformat() for f in fechas],
        "fuentes": {
            "tiempo": "Open-Meteo (open-meteo.com), CC BY 4.0; segundo modelo: ECMWF IFS",
            "aire": "CAMS vía Open-Meteo Air Quality",
            "contaminacion": "World Atlas of Artificial Night Sky Brightness 2025, D. Lorenz (VIIRS)",
            "mapa": "© colaboradores de OpenStreetMap (ODbL)",
            "fotos": "Wikimedia Commons (autor y licencia en cada foto)",
        },
        "spots": salida,
    }


def mejores(informe: dict, fecha: str, n: int = 5) -> list[tuple[float, str, str]]:
    filas = []
    for s in informe["spots"]:
        for d in s["dias"]:
            if d["fecha"] == fecha:
                filas += [(v["nota"], k, s["nombre"]) for k, v in d["notas"].items()]
    return sorted(filas, reverse=True)[:n]


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--spots", default="public/datos/spots.geojson")
    p.add_argument("--mis-spots", default="mis_spots.csv")
    p.add_argument("--dias", type=int, default=DIAS_POR_DEFECTO)
    p.add_argument("--tz", default="Europe/Madrid")
    p.add_argument("--salida", default="public/datos/informe.json")
    p.add_argument("--top", type=int, default=5, help="mejores por día en pantalla")
    a = p.parse_args()

    try:
        spots = cargar_spots(Path(a.spots), Path(a.mis_spots))
    except SystemExit as e:   # aún no hay spots (primera ejecución): no es un fallo del workflow
        print(e)
        return
    print(f"Evaluando {len(spots)} spots para {a.dias} días…")
    informe = evaluar(spots, a.dias, a.tz)
    escribir_json(Path(a.salida), informe)
    for fecha in informe["fechas"]:
        print(f"\n== {fecha} ==")
        for nota, momento, nombre in mejores(informe, fecha, a.top):
            print(f"  {nota:4.1f}  {momento:9}  {nombre}")
    print(f"\nInforme en {a.salida} ({Path(a.salida).stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
