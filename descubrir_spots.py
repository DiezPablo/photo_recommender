#!/usr/bin/env python3
"""
descubrir_spots.py — Descubre spots de fotografía de paisaje a partir de fotos
geolocalizadas de Wikimedia Commons y de miradores de OpenStreetMap.

No necesita ninguna clave de API.

Pipeline:
  1. Commons: fotos geolocalizadas dentro de la bbox (troceada en teselas de ~8 km,
     el máximo que admite la búsqueda geográfica).
  2. Filtro de paisaje: nos quedamos con las fotos de calidad reconocida por la
     comunidad (Quality / Valued / Featured) o cuyas categorías hablan de paisaje,
     y descartamos interiores, retratos, mapas, fauna y flora de primer plano...
  3. DBSCAN (haversine): agrupa las fotos en spots; exige varios autores distintos.
  4. Luz: con la fecha de captura (EXIF) y astral clasificamos cada foto en
     amanecer / atardecer / noche / día → para qué momento es bueno cada spot.
  5. OSM (Overpass): nombra los clusters con el mirador/cumbre/embalse más cercano
     y añade como spots los miradores sin fotos (con menos peso).
  6. Contaminación lumínica de cada spot (atlas de D. Lorenz, contaminacion.py).
  7. Salida: spots.geojson (para condiciones.py y la web) y spots.csv.

Uso:
  pip install -r requirements.txt
  python descubrir_spots.py                          # Sierra de Madrid por defecto
  python descubrir_spots.py --zona "Costa da Morte" --bbox=-9.35,42.85,-8.9,43.35
  python descubrir_spots.py --sin-miradores          # solo spots con fotos

Con coordenadas negativas escribe --bbox= pegado. Las respuestas de las APIs se
guardan en ./cache para no repetir llamadas.
"""
from __future__ import annotations

import argparse
import hashlib
import html as htmlmod
import json
import math
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
from astral import Observer
from astral.sun import sun
from sklearn.cluster import DBSCAN

from comun import USER_AGENT as USER_AGENT_DEFECTO, escribir_json, id_spot
from contaminacion import contaminacion

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# Overpass tiene varios espejos públicos; si uno falla o corta la conexión probamos el siguiente
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
RADIO_TIERRA_M = 6_371_000
# Wikimedia pide identificarse con un User-Agent descriptivo
USER_AGENT = os.environ.get("USER_AGENT", USER_AGENT_DEFECTO)
SESION = requests.Session()
SESION.headers["User-Agent"] = USER_AGENT

COMMONS_REINTENTOS = 15
COMMONS_PAUSA_S = 1.0  # entre peticiones: la API pública limita por IP
FOTOS_POR_SPOT = 6
TESELA_GRADOS = 0.07   # ~8 km: la geosearch de Commons limita el tamaño de la caja

CATEGORIAS_CALIDAD = ("quality images", "valued images", "featured pictures")
PALABRAS_PAISAJE = (
    "landscape", "paisaje", "sunset", "sunrise", "atardecer", "amanecer", "puesta de sol",
    "mountain", "montaña", "sierra", "view", "vista", "mirador", "panoram", "skyline",
    "night sky", "milky way", "vía láctea", "star trail", "astrophoto", "fog", "niebla", "mist",
    "cloud", "nubes", "lake", "lago", "laguna", "reservoir", "embalse", "river", "río",
    "waterfall", "cascada", "valley", "valle", "forest", "bosque", "peak", "pico", "summit",
    "coast", "costa", "beach", "playa", "cliff", "acantilado", "lighthouse", "faro",
    "natural park", "parque natural", "national park", "parque nacional", "snow", "nieve",
    "autumn", "otoño", "dehesa", "meadow", "pradera", "gorge", "garganta", "cañón", "hoces",
)
# Ojo con subcadenas: "aves" casaría con "waves" y "map" con "maple", por eso van en plural/completas
PALABRAS_EXCLUIR = (
    "interior", "portrait", "retrato", "people", "logos", "maps", "mapas", "diagrams",
    "coats of arms", "escudo", "museum", "museo", "food", "insects", "birds",
    "flowers", "plaques", "placas", "signs", "vehicles", "trains", "buses",
    "aircraft", "documents", "postage stamps", "paintings",
    # vistos en la primera ejecución real (Sierra de Madrid, oct-2026):
    "from space", "iss expedition", "aurora viewed", "earth at night",       # fotos de la ISS geolocalizadas
    "grand prix", "motorsport", "rail transport", "railway stations", "avant ",
    "animals", "mammals", "reptiles", "snakes", "coronella", "ciconia", "storks", "fungi",
    "mushrooms", "plants of", "churches", "iglesia", "chapels", "ermita",
    "plaza mayor", "streets", "calles", "festivals", "fiestas", "celebrations", "town halls",
    "casas consistoriales", "sculptures", "esculturas", "graffiti", "schools", "instituto",
    "education", "educación", "skiers", "esquiadores", "sports", "deportes",
)
# Categorías que no sirven como nombre de un spot (demasiado genéricas o administrativas)
CATEGORIAS_NO_NOMBRE = re.compile(
    r"quality|valued|featured|images|photographs|taken (in|on|with)|by user|uploaded|panoramio|"
    r"^\d{4}|\b(19|20)\d\d\b|in the community of|of the community of|in spain|of spain|"
    r"special area|national park|parque nacional|sierra de guadarrama$|sierra norte$|"
    r"province of|provincia de|^landscapes|^views of (the )?(community|province)|clouds|snow|"
    r"cc-by|gfdl|self-published|pd-|license|^files|^media|wikimedia|wiki loves|^(spain|españa|madrid|segovia)$",
    re.I)

# Elementos OSM interesantes para paisaje
FILTROS_OSM = [
    'node["tourism"="viewpoint"]',
    'node["natural"="peak"]["name"]',
    'node["waterway"="waterfall"]',
    'node["man_made"="lighthouse"]',
    'way["natural"="beach"]["name"]',
    'node["natural"="cape"]',
    'way["natural"="cliff"]["name"]',
    'way["water"="lake"]["name"]',
    'way["landuse"="reservoir"]["name"]',
]


# ---------------------------------------------------------------- caché ----
CACHE = Path("cache")


def _cache_get(clave: str):
    f = CACHE / f"{hashlib.sha1(clave.encode()).hexdigest()}.json"
    return json.loads(f.read_text()) if f.exists() else None


def _cache_set(clave: str, datos) -> None:
    CACHE.mkdir(exist_ok=True)
    f = CACHE / f"{hashlib.sha1(clave.encode()).hexdigest()}.json"
    f.write_text(json.dumps(datos))


# -------------------------------------------------------------- Commons ----
def _commons(params: dict) -> dict:
    """Llamada a la API de Commons con caché, maxlag y reintentos amables."""
    params = {"action": "query", "format": "json", "formatversion": 2, "maxlag": 5, **params}
    clave = "commons:" + json.dumps(params, sort_keys=True)
    datos = _cache_get(clave)
    if datos is not None:
        return datos
    for intento in range(COMMONS_REINTENTOS):
        try:
            r = SESION.get(COMMONS_API, params=params, timeout=60)
        except requests.RequestException as e:
            print(f"      Commons: {e.__class__.__name__}, reintento", flush=True)
            time.sleep(10 * (intento + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500 or '"maxlag"' in r.text[:300]:
            # Respetamos lo que pide el servidor (Retry-After) y si no, espera creciente
            espera = int(r.headers.get("Retry-After", 0) or 0) or 10 * (intento + 1)
            print(f"      Commons pide esperar ({r.status_code}): {espera} s", flush=True)
            time.sleep(min(espera, 120) + 1)
            continue
        r.raise_for_status()
        datos = r.json()
        if "error" in datos:
            info = datos["error"].get("info", "")
            if "busy" in info or datos["error"].get("code") in ("maxlag", "ratelimited"):
                print(f"      Commons ocupado ({info}); espero", flush=True)
                time.sleep(15 * (intento + 1))
                continue
            raise RuntimeError(f"Commons: {info}")
        _cache_set(clave, datos)
        time.sleep(COMMONS_PAUSA_S)
        return datos
    raise RuntimeError("Commons no responde (demasiados reintentos)")


def _teselas(bbox, paso=TESELA_GRADOS):
    """Divide la bbox (min_lon, min_lat, max_lon, max_lat) en teselas de `paso` grados."""
    x0, y0, x1, y1 = bbox
    nx, ny = max(1, math.ceil((x1 - x0) / paso)), max(1, math.ceil((y1 - y0) / paso))
    dx, dy = (x1 - x0) / nx, (y1 - y0) / ny
    for i in range(nx):
        for j in range(ny):
            yield (x0 + i * dx, y0 + j * dy, x0 + (i + 1) * dx, y0 + (j + 1) * dy)


def geobuscar_commons(bbox) -> dict[int, dict]:
    """pageid → {titulo, lat, lon} de todos los ficheros geolocalizados en la bbox."""
    fotos: dict[int, dict] = {}

    def buscar(t, profundidad=0):
        x0, y0, x1, y1 = t
        datos = _commons({"list": "geosearch", "gsnamespace": 6, "gslimit": 500,
                          "gsbbox": f"{y1:.5f}|{x0:.5f}|{y0:.5f}|{x1:.5f}"})  # arriba|izq|abajo|der
        res = datos.get("query", {}).get("geosearch", [])
        for g in res:
            fotos[g["pageid"]] = {"titulo": g["title"], "lat": g["lat"], "lon": g["lon"]}
        if len(res) >= 500 and profundidad < 3:  # tope alcanzado: partir en 4 y repetir
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            for sub in ((x0, y0, mx, my), (mx, y0, x1, my), (x0, my, mx, y1), (mx, my, x1, y1)):
                buscar(sub, profundidad + 1)

    teselas = list(_teselas(bbox))
    for n, t in enumerate(teselas, 1):
        buscar(t)
        if n % 10 == 0 or n == len(teselas):
            print(f"      teselas {n}/{len(teselas)} · {len(fotos)} ficheros", flush=True)
    return fotos


def _texto_plano(v: str | None) -> str:
    return re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", "", v or ""))).strip()


def _fecha_exif(v: str | None):
    m = re.search(r"(\d{4})[-:](\d{2})[-:](\d{2})[ T](\d{2}):(\d{2})", _texto_plano(v))
    if not m:
        return pd.NaT
    try:
        return pd.Timestamp(*map(int, m.groups()))
    except ValueError:
        return pd.NaT


def detalles_commons(pageids: list[int]) -> list[dict]:
    """Categorías, autor, licencia, fecha de captura y miniatura de cada fichero."""
    filas = []
    for i in range(0, len(pageids), 50):
        lote = pageids[i:i + 50]
        paginas: dict[int, dict] = {}
        params = {"pageids": "|".join(map(str, lote)), "prop": "imageinfo|categories",
                  "iiprop": "url|user|extmetadata", "iiurlwidth": 640,
                  "iiextmetadatafilter": "DateTimeOriginal|Artist|LicenseShortName|ObjectName",
                  "cllimit": "max", "clshow": "!hidden"}
        cont: dict = {}
        while True:  # las categorías vienen paginadas con 'continue'
            datos = _commons({**params, **cont})
            for p in datos.get("query", {}).get("pages", []):
                acc = paginas.setdefault(p["pageid"], {"cats": [], "info": None, "titulo": p.get("title")})
                acc["cats"] += [c["title"].removeprefix("Category:") for c in p.get("categories", [])]
                if p.get("imageinfo"):
                    acc["info"] = p["imageinfo"][0]
            if "continue" not in datos:
                break
            cont = datos["continue"]
        for pid, p in paginas.items():
            ii = p["info"] or {}
            meta = ii.get("extmetadata", {})
            filas.append({
                "id": pid,
                "titulo": _texto_plano(meta.get("ObjectName", {}).get("value")) or
                          (p["titulo"] or "").removeprefix("File:").rsplit(".", 1)[0],
                "autor_cuenta": ii.get("user"),
                "autor": _texto_plano(meta.get("Artist", {}).get("value")) or ii.get("user"),
                "licencia": _texto_plano(meta.get("LicenseShortName", {}).get("value")),
                "datetaken": _fecha_exif(meta.get("DateTimeOriginal", {}).get("value")),
                "url_m": ii.get("thumburl"),
                "web": ii.get("descriptionurl"),
                "categorias": p["cats"],
            })
        hechos = min(i + 50, len(pageids))
        if hechos % 500 == 0 or hechos == len(pageids):
            print(f"      detalles {hechos}/{len(pageids)}", flush=True)
    return filas


def _patron(palabras) -> re.Pattern:
    # Al inicio de palabra: "río" no casa con "Riofrío" ni "map" con "maple", pero sí admite plurales
    return re.compile(r"(?<![\w])(?:" + "|".join(re.escape(p.strip()) for p in palabras) + ")", re.I)


_RE_PAISAJE = _patron(PALABRAS_PAISAJE)
_RE_EXCLUIR = _patron(PALABRAS_EXCLUIR)


def clasificar_paisaje(categorias: list[str]) -> tuple[bool, bool]:
    """(es_paisaje, es_de_calidad) a partir de las categorías del fichero."""
    cats = " | ".join(categorias).lower()
    calidad = any(c in cats for c in CATEGORIAS_CALIDAD)
    excluir = bool(_RE_EXCLUIR.search(cats))
    paisaje = bool(_RE_PAISAJE.search(cats))
    return (calidad or paisaje) and not excluir, calidad


def descargar_commons(bbox) -> pd.DataFrame:
    """Todas las fotos geolocalizadas de la bbox con sus categorías (sin filtrar)."""
    geo = geobuscar_commons(bbox)
    # Solo fotos (fuera vídeos, audios, PDF y SVG)
    ids = [pid for pid, g in geo.items()
           if re.search(r"\.(jpe?g|png|tiff?|webp)$", g["titulo"], re.I)]
    if not ids:
        return pd.DataFrame()
    df = pd.DataFrame(detalles_commons(ids))
    df["lat"] = df["id"].map(lambda i: geo[i]["lat"])
    df["lon"] = df["id"].map(lambda i: geo[i]["lon"])
    return df


def filtrar_paisaje(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    clas = df["categorias"].map(clasificar_paisaje)
    df = df.assign(paisaje=clas.map(lambda c: c[0]), calidad=clas.map(lambda c: c[1]),
                   owner=df["autor_cuenta"].fillna(df["autor"]))
    df = df[df.paisaje].copy()
    return df[["id", "owner", "autor", "licencia", "titulo", "lat", "lon", "calidad",
               "datetaken", "url_m", "web", "categorias"]]


def buscar_commons(bbox) -> pd.DataFrame:
    return filtrar_paisaje(descargar_commons(bbox))


# --------------------------------------------------------------- volcado ----
# Las respuestas crudas se vuelcan para poder ajustar filtros y agrupación sin volver a pedir nada
# a Commons (desde el contenedor de desarrollo la API limita mucho): python descubrir_spots.py --desde-volcado DIR
def volcar(dir_: Path, fotos: pd.DataFrame, osm: pd.DataFrame) -> None:
    dir_.mkdir(parents=True, exist_ok=True)
    fotos.assign(datetaken=fotos["datetaken"].astype(str)).to_json(
        dir_ / "fotos_commons.jsonl.gz", orient="records", lines=True, force_ascii=False)
    osm.to_json(dir_ / "osm.jsonl.gz", orient="records", lines=True, force_ascii=False)


def leer_volcado(dir_: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    fotos = pd.read_json(dir_ / "fotos_commons.jsonl.gz", lines=True, dtype={"autor_cuenta": str})
    fotos["datetaken"] = pd.to_datetime(fotos["datetaken"].replace("NaT", None), errors="coerce")
    osm = pd.read_json(dir_ / "osm.jsonl.gz", lines=True, dtype={"direction": str, "ele": str})
    return fotos, osm


# ------------------------------------------------------------ clustering ----
def agrupar(df: pd.DataFrame, radio_m=300, min_fotos=3, min_autores=2) -> pd.DataFrame:
    """DBSCAN con métrica haversine. Devuelve df con columna 'cluster' (-1 = ruido)."""
    coords = np.radians(df[["lat", "lon"]].to_numpy())
    db = DBSCAN(eps=radio_m / RADIO_TIERRA_M, min_samples=min_fotos,
                metric="haversine", algorithm="ball_tree").fit(coords)
    df = df.copy()
    df["cluster"] = db.labels_
    # Fuera clusters de un solo autor (alguien que subió una serie entera del mismo sitio)
    autores = df[df.cluster >= 0].groupby("cluster")["owner"].nunique()
    validos = autores[autores >= min_autores].index
    df.loc[~df.cluster.isin(validos), "cluster"] = -1
    return df


# ------------------------------------------------------------------ luz ----
def momento_de_luz(lat, lon, cuando, tz: ZoneInfo, margen_min=75) -> str:
    if pd.isna(cuando):
        return "desconocido"
    local = cuando.replace(tzinfo=tz) if cuando.tzinfo is None else cuando
    try:
        s = sun(Observer(latitude=lat, longitude=lon), date=local.date(), tzinfo=tz)
    except ValueError:
        return "desconocido"
    m = timedelta(minutes=margen_min)
    if abs(local - s["sunrise"]) <= m:
        return "amanecer"
    if abs(local - s["sunset"]) <= m:
        return "atardecer"
    if local < s["dawn"] or local > s["dusk"]:
        return "noche"
    return "día"


# ------------------------------------------------------------------ OSM ----
def buscar_osm(bbox) -> pd.DataFrame:
    x0, y0, x1, y1 = bbox
    caja = f"({y0},{x0},{y1},{x1})"
    cuerpo = "".join(f"{f}{caja};" for f in FILTROS_OSM)
    consulta = f"[out:json][timeout:90];({cuerpo});out center tags;"
    datos = _cache_get(consulta)
    if datos is None:
        ultimo_error: Exception | None = None
        for url in OVERPASS_URLS:
            try:
                r = SESION.post(url, data={"data": consulta}, timeout=120)
                r.raise_for_status()
                datos = r.json()
                break
            except (requests.RequestException, ValueError) as e:
                print(f"      {url} falla ({e.__class__.__name__}); pruebo otro espejo")
                ultimo_error = e
        if datos is None:
            raise requests.RequestException(f"Ningún espejo de Overpass responde: {ultimo_error}")
        _cache_set(consulta, datos)
    filas = []
    for e in datos.get("elements", []):
        lat = e.get("lat") or e.get("center", {}).get("lat")
        lon = e.get("lon") or e.get("center", {}).get("lon")
        if lat is None:
            continue
        t = e.get("tags", {})
        tipo = (t.get("tourism") or t.get("natural") or t.get("waterway")
                or t.get("man_made") or t.get("water") or t.get("landuse"))
        filas.append({"osm_id": f"{e['type']}/{e['id']}", "lat": lat, "lon": lon,
                      "nombre": t.get("name"), "tipo": tipo,
                      "ele": t.get("ele"), "direction": t.get("direction")})
    return pd.DataFrame(filas)


def _haversine_m(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * RADIO_TIERRA_M * np.arcsin(np.sqrt(a))


# ------------------------------------------------------------ resumen ----
TIPOS_ES = {"viewpoint": "mirador", "peak": "cumbre", "waterfall": "cascada",
            "lighthouse": "faro", "beach": "playa", "cape": "cabo",
            "cliff": "acantilado", "lake": "lago", "reservoir": "embalse", "water": "lago",
            "attraction": "paraje"}


def limpiar_nombre(t: str) -> str:
    """Título de foto → nombre de spot: sin ids de Flickr, fechas, numeración ni 'panoramio'."""
    t = re.sub(r"\((?:[^()]*\d{4}[^()]*|\d+)\)", " ", t)           # (6495112213), (2 de mayo de 2015, …)
    t = re.sub(r"\b(?:19|20)\d\d[-_.]\d\d[-_.]\d\d\b", " ", t)    # 2011-06-05
    t = re.sub(r"(?i)\s*-?\s*panoramio\b.*$", " ", t)
    t = re.sub(r"(?i)\b(?:retouched|cropped|by[- ]\S+|img|dsc|p\d{6,})\b", " ", t)
    t = re.sub(r"[_]+", " ", t)
    t = re.sub(r"(?<=[a-záéíóúñ])(?=[A-ZÁÉÍÓÚÑ][a-záéíóúñ])", " ", t)   # LaSierra → La Sierra
    t = re.sub(r"(?:\s*[-–]\s*|\s+)\d{1,3}$", "", t.strip())         # " - 01", " 09", "Pirón2"
    t = re.sub(r"(?<=[a-záéíóúñ])\d{1,2}$", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" -–,.")
    if t.isupper():
        t = t.title().replace(" De ", " de ").replace(" Del ", " del ").replace(" La ", " la ").replace(" El ", " el ")
    return t[:70]


def categoria_nombre(categorias: pd.Series, n_fotos: int) -> str | None:
    """La categoría específica más repetida en el cluster (p. ej. 'Laguna Grande de Peñalara'),
    si la comparten al menos el 35 % de las fotos."""
    cuenta: dict[str, int] = {}
    for cats in categorias:
        for c in set(cats):
            if not CATEGORIAS_NO_NOMBRE.search(c) and not _RE_EXCLUIR.search(c):
                cuenta[c] = cuenta.get(c, 0) + 1
    if not cuenta:
        return None
    mejor = max(cuenta, key=lambda c: (cuenta[c], -len(c)))
    return traducir_categoria(mejor) if cuenta[mejor] >= max(2, 0.35 * n_fotos) else None


# Muchas categorías de Commons están en inglés: patrones habituales al castellano
_TRADUCCIONES = (
    (r"^Views (?:of|from) (?:the )?(.+)$", r"\1"),
    (r"^Landscapes of (.+)$", r"\1"),
    (r"^(.+) Reservoir$", r"Embalse de \1"),
    (r"^Bridges over (?:the )?(.+) River$", r"Puentes sobre el río \1"),
    (r"^(.+) River in (.+)$", r"Río \1 en \2"),
    (r"^(.+) River$", r"Río \1"),
    (r"^(.+) Valley$", r"Valle de \1"),
    (r"^Monastery of (.+)$", r"Monasterio de \1"),
    (r"^Lake (.+)$", r"Lago \1"),
)


def traducir_categoria(c: str) -> str:
    for _ in range(3):   # "Views of Monastery of X" → "Monastery of X" → "Monasterio de X"
        anterior = c
        for patron, cambio in _TRADUCCIONES:
            c = re.sub(patron, cambio, c)
        if c == anterior:
            break
    return c


def resumir_spots(fotos: pd.DataFrame, osm: pd.DataFrame, tz: ZoneInfo,
                  radio_nombre_m=600, radio_osm_seguro_m=400) -> pd.DataFrame:
    f = fotos[fotos.cluster >= 0].copy()
    if f.empty:
        return pd.DataFrame()
    f["luz"] = [momento_de_luz(a, o, d, tz) for a, o, d in zip(f.lat, f.lon, f.datetaken)]
    spots = []
    for cid, g in f.groupby("cluster"):
        lat, lon = g.lat.median(), g.lon.median()
        luz = g[g.luz != "desconocido"].luz.value_counts(normalize=True)
        # Fotos de ejemplo: primero las de calidad reconocida, y a ser posible de autores distintos
        candidatas = g.sort_values(["calidad", "datetaken"], ascending=[False, False]).dropna(subset=["url_m"])
        top = pd.concat([candidatas.drop_duplicates("owner"), candidatas]).drop_duplicates("id").head(FOTOS_POR_SPOT)
        meses = g.datetaken.dropna().dt.month.value_counts()
        autores = g.owner.nunique()
        n_calidad = int(g.calidad.sum())
        spot = {
            "spot_id": int(cid), "lat": round(lat, 5), "lon": round(lon, 5),
            "origen": "commons", "fotos": len(g), "fotografos": autores,
            "fotos_calidad": n_calidad,
            # Puntuación: autores distintos y fotos de calidad pesan más que el volumen
            "puntuacion": round(2 * math.log1p(autores) + math.log1p(len(g))
                                + 1.5 * math.log1p(n_calidad), 2),
            "mejor_momento": luz.idxmax() if not luz.empty else "desconocido",
            "pct_amanecer": round(luz.get("amanecer", 0) * 100),
            "pct_atardecer": round(luz.get("atardecer", 0) * 100),
            "pct_noche": round(luz.get("noche", 0) * 100),
            "meses": [int(meses.get(m, 0)) for m in range(1, 13)],
            "meses_top": [int(m) for m in meses.head(3).index],
            "galeria": [{"url": r.url_m, "enlace": r.web, "autor": (r.autor or r.owner or "")[:80],
                         "licencia": r.licencia or "", "titulo": (r.titulo or "")[:120],
                         "fecha": r.datetaken.strftime("%Y-%m-%d") if not pd.isna(r.datetaken) else None}
                        for r in top.itertuples()],
            "nombre": None, "tipo_osm": None, "dist_osm_m": None, "direccion_vista": None,
        }
        # Nombre: elemento OSM con nombre muy cerca > categoría de Commons compartida > OSM a < 600 m
        # > título limpio de la mejor foto
        cat = categoria_nombre(g.categorias, len(g)) if "categorias" in g else None
        if not osm.empty:
            d = _haversine_m(lat, lon, osm.lat.to_numpy(), osm.lon.to_numpy())
            cerca = osm.assign(d=d)[(d <= radio_nombre_m)].sort_values("d")
            con_nombre = cerca[cerca.nombre.map(lambda x: isinstance(x, str) and bool(x.strip()))]
            e = con_nombre.iloc[0] if not con_nombre.empty else (cerca.iloc[0] if not cerca.empty else None)
            if e is not None:
                spot.update(tipo_osm=TIPOS_ES.get(e.tipo, e.tipo), dist_osm_m=int(e.d),
                            direccion_vista=e.direction if isinstance(e.direction, str) else None)
                if isinstance(e.nombre, str) and e.nombre.strip() and (e.d <= radio_osm_seguro_m or not cat):
                    spot["nombre"] = e.nombre.strip()
        if not spot["nombre"] and cat:
            spot["nombre"] = cat
            if not spot["tipo_osm"]:
                spot["tipo_osm"] = tipo_por_nombre(cat)
        if not isinstance(spot["nombre"], str) or not spot["nombre"].strip():
            # Último recurso: el título de la foto de mejor calidad, limpio
            spot["nombre"] = limpiar_nombre(top.titulo.iloc[0] if not top.empty else g.titulo.iloc[0])
            if not spot["tipo_osm"]:
                spot["tipo_osm"] = tipo_por_nombre(spot["nombre"])
        spots.append(spot)
    # Nombres repetidos (dos clusters en el mismo embalse): numerarlos para distinguirlos
    vistos: dict[str, int] = {}
    for sp in sorted(spots, key=lambda x: -x["puntuacion"]):
        n = vistos.get(sp["nombre"], 0) + 1
        vistos[sp["nombre"]] = n
        if n > 1:
            sp["nombre"] = f"{sp['nombre']} ({n})"
    # Nombres repetidos (dos clusters en el mismo embalse): numerarlos para distinguirlos
    vistos: dict[str, int] = {}
    for sp in sorted(spots, key=lambda x: -x["puntuacion"]):
        n = vistos.get(sp["nombre"], 0) + 1
        vistos[sp["nombre"]] = n
        if n > 1:
            sp["nombre"] = f"{sp['nombre']} ({n})"
    return pd.DataFrame(spots).sort_values("puntuacion", ascending=False)


TIPOS_POR_PALABRA = (("embalse", "embalse"), ("reservoir", "embalse"), ("presa", "embalse"),
                     ("laguna", "lago"), ("lago", "lago"), ("lake", "lago"), ("cascada", "cascada"),
                     ("waterfall", "cascada"), ("chorr", "cascada"), ("río", "río"), ("river", "río"),
                     ("mirador", "mirador"), ("pico", "cumbre"), ("peak", "cumbre"), ("puente", "puente"),
                     ("bridge", "puente"), ("playa", "playa"), ("faro", "faro"))


def tipo_por_nombre(nombre: str) -> str | None:
    n = nombre.lower()
    return next((t for palabra, t in TIPOS_POR_PALABRA if palabra in n), None)


def miradores_sin_fotos(osm: pd.DataFrame, spots: pd.DataFrame, radio_m=800) -> pd.DataFrame:
    if osm.empty:
        return osm
    v = osm[osm.tipo == "viewpoint"].copy()
    if spots.empty or v.empty:
        return v
    dmin = [(_haversine_m(r.lat, r.lon, spots.lat.to_numpy(), spots.lon.to_numpy())).min()
            for r in v.itertuples()]
    return v[np.array(dmin) > radio_m]


def nombrar_miradores(miradores: pd.DataFrame, osm: pd.DataFrame, radio_m=2500) -> pd.DataFrame:
    """Los miradores sin nombre toman el del elemento OSM con nombre más cercano ('Mirador junto a
    Pico X'); si no hay ninguno a menos de 2,5 km se descartan (sin fotos ni nombre aportan poco)."""
    con_nombre = osm[osm.nombre.map(lambda x: isinstance(x, str) and bool(x.strip())) & (osm.tipo != "viewpoint")]
    nombres = []
    for r in miradores.itertuples():
        if isinstance(r.nombre, str) and r.nombre.strip():
            nombres.append(r.nombre.strip())
            continue
        if con_nombre.empty:
            nombres.append(None)
            continue
        d = _haversine_m(r.lat, r.lon, con_nombre.lat.to_numpy(), con_nombre.lon.to_numpy())
        i = int(np.argmin(d))
        nombres.append(f"Mirador junto a {con_nombre.nombre.iloc[i]}" if d[i] <= radio_m else None)
    out = miradores.assign(nombre=nombres)
    return out[out.nombre.notna()]


def miradores_como_spots(miradores: pd.DataFrame, id_inicial: int) -> pd.DataFrame:
    """Miradores de OSM sin fotos, como spots de segunda fila (nota de condiciones sí, fama no)."""
    filas = []
    for k, r in enumerate(miradores.itertuples()):
        filas.append({
            "spot_id": id_inicial + k, "lat": round(r.lat, 5), "lon": round(r.lon, 5),
            "origen": "osm", "fotos": 0, "fotografos": 0, "fotos_calidad": 0,
            "puntuacion": 0.5, "mejor_momento": "desconocido",
            "pct_amanecer": 0, "pct_atardecer": 0, "pct_noche": 0,
            "meses": [0] * 12, "meses_top": [], "galeria": [],
            "nombre": r.nombre if isinstance(r.nombre, str) else "Mirador",
            "tipo_osm": "mirador", "dist_osm_m": 0,
            "direccion_vista": r.direction if isinstance(r.direction, str) else None,
        })
    return pd.DataFrame(filas)


# --------------------------------------------------------------- salida ----
def guardar(spots: pd.DataFrame, salida: Path, zona: str):
    """spots.geojson (lo leen condiciones.py y la web) y spots.csv para revisar a mano."""
    salida.mkdir(parents=True, exist_ok=True)
    features = []
    for r in spots.to_dict("records"):
        lat, lon = r.pop("lat"), r.pop("lon")
        r["id"] = id_spot(r["nombre"], lat, lon)
        try:
            r["contaminacion"] = contaminacion(lat, lon)
        except requests.RequestException as e:
            print(f"      sin atlas de contaminación para {r['nombre']}: {e}")
            r["contaminacion"] = None
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                         "properties": r})
    escribir_json(salida / "spots.geojson",
                  {"type": "FeatureCollection", "zona": zona, "features": features}, indent=1)
    spots.drop(columns=["galeria", "meses"], errors="ignore").to_csv(salida / "spots.csv", index=False)


# ------------------------------------------------------------------ main ----
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--zona", default="Sierra de Madrid")
    p.add_argument("--bbox", default="-4.30,40.60,-3.55,41.10",
                   help="min_lon,min_lat,max_lon,max_lat (con negativos: --bbox=...)")
    p.add_argument("--radio", type=int, default=300, help="radio DBSCAN en metros")
    p.add_argument("--min-fotos", type=int, default=3)
    p.add_argument("--min-autores", type=int, default=2)
    p.add_argument("--sin-miradores", action="store_true",
                   help="no añadir miradores de OSM sin fotos como spots")
    p.add_argument("--tz", default="Europe/Madrid")
    p.add_argument("--salida", default="salida")
    p.add_argument("--desde-volcado", metavar="DIR",
                   help="no pedir nada a las APIs: usar el volcado de una ejecución anterior")
    a = p.parse_args()

    bbox = tuple(float(v) for v in a.bbox.split(","))
    tz = ZoneInfo(a.tz)

    salida = Path(a.salida)
    if a.desde_volcado:
        crudas, osm = leer_volcado(Path(a.desde_volcado))
        print(f"[1/4] Volcado: {len(crudas)} fotos geolocalizadas y {len(osm)} elementos OSM")
    else:
        print(f"[1/4] Wikimedia Commons: buscando fotos en {a.zona}…")
        crudas = descargar_commons(bbox)
        print("      OpenStreetMap: miradores, cumbres, cascadas…")
        try:
            osm = buscar_osm(bbox)
        except requests.RequestException as e:
            print(f"      Overpass no responde ({e}); sigo sin OSM")
            osm = pd.DataFrame()
        volcar(salida / "volcado", crudas, osm)
    fotos = filtrar_paisaje(crudas)
    print(f"      {len(crudas)} fotos geolocalizadas → {len(fotos)} de paisaje ({int(fotos.calidad.sum()) if not fotos.empty else 0} de calidad)")

    print("[2/4] Agrupando en spots (DBSCAN)…")
    if not fotos.empty:
        fotos = agrupar(fotos, a.radio, a.min_fotos, a.min_autores)
        n = fotos.cluster.nunique() - (1 if -1 in fotos.cluster.values else 0)
    else:
        n = 0
    print(f"      {n} clusters válidos")

    print(f"[3/4] OpenStreetMap: {len(osm)} elementos")

    print("[4/4] Resumiendo spots y contaminación lumínica…")
    spots = resumir_spots(fotos, osm, tz) if n else pd.DataFrame()
    miradores = miradores_sin_fotos(osm, spots)
    if not miradores.empty:
        miradores = nombrar_miradores(miradores, osm)
    if not a.sin_miradores and not miradores.empty:
        extra = miradores_como_spots(miradores, int(spots.spot_id.max()) + 1 if not spots.empty else 0)
        spots = pd.concat([spots, extra], ignore_index=True) if not spots.empty else extra
    if spots.empty:
        raise SystemExit("No salen spots: prueba una zona más grande o baja --min-fotos / --min-autores")
    guardar(spots, salida, a.zona)

    con_fotos = spots[spots.origen == "commons"]
    print(f"\n{len(con_fotos)} spots con fotos · {len(spots) - len(con_fotos)} miradores OSM → {salida}/spots.geojson\n")
    if not con_fotos.empty:
        print(con_fotos[["nombre", "tipo_osm", "fotografos", "fotos", "fotos_calidad",
                         "mejor_momento", "puntuacion"]].head(15).to_string(index=False))


if __name__ == "__main__":
    main()
