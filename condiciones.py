#!/usr/bin/env python3
"""
condiciones.py — Condiciones y nota diaria (0-10) de cada spot para foto de paisaje y nocturna.

Lee los spots (spots.geojson de descubrir_spots.py y mis_spots.csv con los tuyos), pide la
previsión horaria a Open-Meteo y calcula sol, luna y Vía Láctea (astro.py). Para cada spot y día:

  - amanecer / atardecer: nubes por capas en el spot y nubes bajas en el HORIZONTE, a ~40 km en
    la dirección del sol (si allí hay un banco de nubes bajas el sol no ilumina el cielo).
  - astro (noche estrellada / Vía Láctea): nubes, luna (y ventana sin luna), contaminación
    lumínica del atlas, humedad, viento, rocío y núcleo de la Vía Láctea.
  - niebla: humedad, margen hasta el punto de rocío y viento de madrugada; mar de nubes si el
    spot está alto y hay nubes bajas alrededor.

Cada nota lleva su desglose (puntuacion.py) para que la web explique qué suma y qué resta.

Uso:
  python condiciones.py                                   # 5 días → public/datos/informe.json
  python condiciones.py --dias 3 --spots public/datos/spots.geojson --mis-spots mis_spots.csv

mis_spots.csv (opcional): nombre,lat,lon[,tipo]   (las líneas que empiezan por # se ignoran)
Open-Meteo es gratuito y sin clave para uso no comercial.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

import astro
from comun import USER_AGENT, escribir_json, id_spot
from contaminacion import contaminacion
from puntuacion import _v, nota_astro, nota_luz, nota_niebla

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
VARIABLES = [
    "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high",
    "visibility", "precipitation_probability", "wind_speed_10m", "wind_gusts_10m",
    "relative_humidity_2m", "dew_point_2m", "temperature_2m",
]
KM_HORIZONTE = 40          # distancia del punto de control del horizonte
LOTE_COORDS = 100          # coordenadas por petición a Open-Meteo
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
    return None if x is None else round(x, n) if n else int(round(x))


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
                          "contaminacion": p.get("contaminacion")})
    if csv and csv.exists():
        df = pd.read_csv(csv, comment="#", skip_blank_lines=True)
        for r in df.itertuples():
            tipo = getattr(r, "tipo", None)
            spots.append({"id": id_spot(r.nombre, float(r.lat), float(r.lon)), "nombre": r.nombre,
                          "lat": float(r.lat), "lon": float(r.lon),
                          "tipo": tipo if isinstance(tipo, str) else None,
                          "origen": "propio", "contaminacion": None})
    if not spots:
        raise SystemExit("No hay spots: ejecuta descubrir_spots.py o añade alguno a mis_spots.csv")
    vistos, unicos = set(), []
    for s in spots:
        if s["id"] not in vistos:
            vistos.add(s["id"])
            unicos.append(s)
    return unicos


# -------------------------------------------------------------- tiempo ----
def _cache_get(clave, max_edad_s=2 * 3600):
    f = CACHE / f"om_{hashlib.sha1(clave.encode()).hexdigest()}.json"
    if f.exists() and time.time() - f.stat().st_mtime < max_edad_s:
        return json.loads(f.read_text())
    return None


def _cache_set(clave, datos):
    CACHE.mkdir(exist_ok=True)
    (CACHE / f"om_{hashlib.sha1(clave.encode()).hexdigest()}.json").write_text(json.dumps(datos))


def pedir_tiempo(coords: list[tuple[float, float]], dias: int, tz_nombre: str) -> list[dict]:
    """Previsión horaria para una lista de (lat, lon). Devuelve por coordenada
    {"elevacion": m, "horas": DataFrame indexado por hora local (naive)}."""
    resultados: list[dict] = []
    for i in range(0, len(coords), LOTE_COORDS):
        lote = coords[i:i + LOTE_COORDS]
        params = {
            "latitude": ",".join(str(c[0]) for c in lote),
            "longitude": ",".join(str(c[1]) for c in lote),
            "hourly": ",".join(VARIABLES),
            "timezone": tz_nombre,
            "forecast_days": min(dias + 1, 16),   # +1: la última noche acaba al día siguiente
        }
        clave = json.dumps(params, sort_keys=True)
        datos = _cache_get(clave)
        if datos is None:
            for intento in range(5):
                try:
                    r = requests.get(OPEN_METEO_URL, params=params, timeout=90,
                                     headers={"User-Agent": USER_AGENT})
                except requests.RequestException as e:   # cortes de conexión puntuales
                    print(f"  Open-Meteo: {e.__class__.__name__}, reintento")
                    time.sleep(5 * (intento + 1))
                    continue
                if r.status_code in (429, 502, 503, 504):
                    time.sleep(10 * (intento + 1))
                    continue
                r.raise_for_status()
                datos = r.json()
                break
            if datos is None:
                raise SystemExit("Open-Meteo no responde")
            _cache_set(clave, datos)
        if isinstance(datos, dict):      # una sola coordenada → objeto, varias → lista
            datos = [datos]
        for d in datos:
            df = pd.DataFrame(d["hourly"])
            df["time"] = pd.to_datetime(df["time"])
            resultados.append({"elevacion": d.get("elevation"), "horas": df.set_index("time")})
    return resultados


def fila_en(df: pd.DataFrame, t: datetime) -> dict:
    """Valores de la hora más cercana a t (interpolar no aporta: el modelo es horario)."""
    t = pd.Timestamp(t.replace(tzinfo=None))
    return df.iloc[df.index.get_indexer([t], method="nearest")[0]].to_dict()


def filas_entre(df: pd.DataFrame, ini: datetime, fin: datetime) -> pd.DataFrame:
    return df.loc[pd.Timestamp(ini.replace(tzinfo=None)):pd.Timestamp(fin.replace(tzinfo=None))]


def _meteo_momento(f: dict, hz: dict) -> dict:
    return {"nubes_bajas": _r(_v(f, "cloud_cover_low")), "nubes_medias": _r(_v(f, "cloud_cover_mid")),
            "nubes_altas": _r(_v(f, "cloud_cover_high")), "nubes_horizonte": _r(_v(hz, "cloud_cover_low")),
            "visibilidad_km": _r(_v(f, "visibility", 24000) / 1000, 1),
            "lluvia": _r(_v(f, "precipitation_probability")), "viento": _r(_v(f, "wind_speed_10m")),
            "temperatura": _r(_v(f, "temperature_2m"), 1), "humedad": _r(_v(f, "relative_humidity_2m"))}


# ------------------------------------------------------------- informe ----
def _horizontes(spot: dict, dia0: date, tz: ZoneInfo) -> dict:
    sol0 = astro.calcular_sol(spot["lat"], spot["lon"], dia0, tz)
    # El azimut del sol cambia menos de 1° al día: usamos el del primer día para todo el informe.
    # Redondeamos a 0,05° (~5 km, menos que la rejilla del modelo) para compartir peticiones.
    out = {}
    for k, az in (("amanecer", sol0.az_amanecer), ("atardecer", sol0.az_atardecer)):
        if az is not None:
            la, lo = astro.punto_destino(spot["lat"], spot["lon"], az, KM_HORIZONTE)
            out[k] = (round(la * 20) / 20, round(lo * 20) / 20)
    return out


def evaluar_spot_dia(spot: dict, dia: date, indice: int, tz: ZoneInfo,
                     df: pd.DataFrame, hz: dict[str, pd.DataFrame], elevacion: float | None) -> dict:
    sol = astro.calcular_sol(spot["lat"], spot["lon"], dia, tz)
    noche = astro.calcular_noche(spot["lat"], spot["lon"], dia, tz, sol)
    es_agua = (spot.get("tipo") or "") in TIPOS_AGUA
    notas, meteo, avisos = {}, {}, []

    for momento, hora in (("amanecer", sol.amanecer), ("atardecer", sol.atardecer)):
        if hora is None or momento not in hz:
            continue
        f, fh = fila_en(df, hora), fila_en(hz[momento], hora)
        n = nota_luz(f, fh, es_agua=es_agua, momento=momento)
        notas[momento] = n.a_dict()
        meteo[momento] = _meteo_momento(f, fh)

    # ---- noche: usamos las horas sin luna si hay al menos una; si no, toda la noche
    lp = (spot.get("contaminacion") or {}).get("zona")
    if noche.ini and noche.fin:
        tramos = [t for t in noche.sin_luna if (t[1] - t[0]).total_seconds() >= 1800] \
            if noche.horas_sin_luna >= 1 else [(noche.ini, noche.fin)]
        horas_utiles = pd.concat([filas_entre(df, a, b) for a, b in tramos]) if tramos else df.iloc[0:0]
        if horas_utiles.empty:
            horas_utiles = filas_entre(df, noche.ini, noche.fin)
        nubes = float(horas_utiles["cloud_cover"].mean()) if not horas_utiles.empty else 100.0
        hum = float(horas_utiles["relative_humidity_2m"].mean()) if not horas_utiles.empty else 0.0
        viento = float(horas_utiles["wind_speed_10m"].mean()) if not horas_utiles.empty else 0.0
        toda = filas_entre(df, noche.ini, noche.fin)
        margen = (toda["temperature_2m"] - toda["dew_point_2m"]) if not toda.empty else pd.Series([99.0])
        n = nota_astro(nubes, hum, viento, float(margen.min()), noche.horas_sin_luna,
                       noche.horas_oscuras, noche.luna_iluminacion, lp, noche.vl_horas_sin_luna)
        notas["astro"] = n.a_dict()
        meteo["noche"] = {
            "nubes": _r(nubes), "humedad": _r(hum), "viento": _r(viento),
            "rachas": _r(float(toda["wind_gusts_10m"].max())) if not toda.empty else None,
            "temp_min": _r(float(toda["temperature_2m"].min()), 1) if not toda.empty else None,
            "punto_rocio": _r(float(toda["dew_point_2m"].max()), 1) if not toda.empty else None,
            "margen_rocio": _r(float(margen.min()), 1),
        }
    else:
        notas["astro"] = nota_astro(100, 0, 0, 99, 0, 0, 0, lp).a_dict()

    if sol.amanecer:
        madrugada = filas_entre(df, sol.amanecer - timedelta(hours=3), sol.amanecer + timedelta(hours=1))
        bajas_alrededor = None
        if hz:
            bajas_alrededor = sum(_v(fila_en(h, sol.amanecer), "cloud_cover_low") for h in hz.values()) / len(hz)
        notas["niebla"] = nota_niebla(madrugada.to_dict("records"), elevacion, bajas_alrededor).a_dict()

    for n in notas.values():
        avisos += [a for a in n["avisos"] if a not in avisos]

    return {
        "fecha": dia.isoformat(), "fiabilidad": fiabilidad(indice),
        "sol": {"amanecer": _hhmm(sol.amanecer), "atardecer": _hhmm(sol.atardecer),
                "az_amanecer": _r(sol.az_amanecer), "az_atardecer": _r(sol.az_atardecer),
                "dorada_manana": _tramo(sol.dorada_manana), "dorada_tarde": _tramo(sol.dorada_tarde),
                "azul_manana": _tramo(sol.azul_manana), "azul_tarde": _tramo(sol.azul_tarde)},
        "noche": {
            "ini": _hhmm(noche.ini), "fin": _hhmm(noche.fin), "horas": _r(noche.horas_oscuras, 1),
            "luna": {"fase": noche.luna_fase, "iluminacion": _r(noche.luna_iluminacion * 100),
                     "edad": _r(noche.luna_edad, 1), "salida": _hhmm(noche.luna_salida),
                     "puesta": _hhmm(noche.luna_puesta),
                     "sin_luna": [_tramo(t) for t in noche.sin_luna],
                     "horas_sin_luna": _r(noche.horas_sin_luna, 1)},
            "via_lactea": {"tramos": [_tramo(t) for t in noche.vl_tramos], "horas": _r(noche.vl_horas, 1),
                           "horas_sin_luna": _r(noche.vl_horas_sin_luna, 1),
                           "altura_max": _r(noche.vl_altura_max), "azimut_max": _r(noche.vl_azimut_max),
                           "hora_max": _hhmm(noche.vl_hora_max),
                           "azimut_ini": _r(noche.vl_azimut_ini), "azimut_fin": _r(noche.vl_azimut_fin)},
        },
        "meteo": meteo, "notas": notas, "avisos": avisos,
    }


def evaluar(spots: list[dict], dias: int, tz_nombre: str, hoy: date | None = None,
            previsiones: list[dict] | None = None) -> dict:
    tz = ZoneInfo(tz_nombre)
    hoy = hoy or datetime.now(tz).date()
    fechas = [hoy + timedelta(days=i) for i in range(dias)]

    for s in spots:
        if s.get("contaminacion") is None:
            try:
                s["contaminacion"] = contaminacion(s["lat"], s["lon"])
            except requests.RequestException as e:
                print(f"  sin atlas de contaminación para {s['nombre']}: {e}")

    # Coordenadas a pedir: cada spot + sus puntos de horizonte (sin repetir)
    coords: list[tuple[float, float]] = []
    pos_coord: dict[tuple[float, float], int] = {}

    def indice(c):
        if c not in pos_coord:
            pos_coord[c] = len(coords)
            coords.append(c)
        return pos_coord[c]

    planes = []
    for s in spots:
        hz = _horizontes(s, fechas[0], tz)
        planes.append({"spot": indice((round(s["lat"], 4), round(s["lon"], 4))),
                       "hz": {k: indice(c) for k, c in hz.items()}, "hz_coord": hz})
    if previsiones is None:
        print(f"  Open-Meteo: {len(coords)} puntos ({len(spots)} spots + horizontes)")
        previsiones = pedir_tiempo(coords, dias, tz_nombre)

    salida = []
    for s, plan in zip(spots, planes):
        p = previsiones[plan["spot"]]
        hz = {k: previsiones[i]["horas"] for k, i in plan["hz"].items()}
        dias_spot = [evaluar_spot_dia(s, d, i, tz, p["horas"], hz, p["elevacion"])
                     for i, d in enumerate(fechas)]
        salida.append({
            "id": s["id"], "nombre": s["nombre"], "lat": round(s["lat"], 5), "lon": round(s["lon"], 5),
            "tipo": s.get("tipo"), "origen": s.get("origen"), "elevacion": _r(p["elevacion"]),
            "contaminacion": s.get("contaminacion"),
            "horizonte": {k: list(c) for k, c in plan["hz_coord"].items()},
            "dias": dias_spot,
        })
    return {
        "generado": datetime.now(tz).isoformat(timespec="minutes"),
        "zona_horaria": tz_nombre,
        "fechas": [f.isoformat() for f in fechas],
        "fuentes": {
            "tiempo": "Open-Meteo (open-meteo.com), CC BY 4.0",
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
