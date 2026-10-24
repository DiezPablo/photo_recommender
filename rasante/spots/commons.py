"""Wikimedia Commons: fotos geolocalizadas cerca de un punto, sus autores, licencias y si son de paisaje.

Amable con la API: caché en disco, maxlag, Retry-After y una pausa entre peticiones (Commons limita por IP;
desde el contenedor de desarrollo responde 429 casi siempre: el descubrimiento real corre en Actions).
"""

from __future__ import annotations

import html as htmlmod
import json
import re
import time

import pandas as pd
import requests

from rasante.comun.cache import CacheJson
from rasante.comun.red import sesion

CACHE = CacheJson()
SESION = sesion()


COMMONS_API = "https://commons.wikimedia.org/w/api.php"


COMMONS_REINTENTOS = 15


COMMONS_PAUSA_S = 1.0  # entre peticiones: la API pública limita por IP


CATEGORIAS_CALIDAD = ("quality images", "valued images", "featured pictures")


PALABRAS_PAISAJE = (
    "landscape",
    "paisaje",
    "sunset",
    "sunrise",
    "atardecer",
    "amanecer",
    "puesta de sol",
    "mountain",
    "montaña",
    "sierra",
    "view",
    "vista",
    "mirador",
    "panoram",
    "skyline",
    "night sky",
    "milky way",
    "vía láctea",
    "star trail",
    "astrophoto",
    "fog",
    "niebla",
    "mist",
    "cloud",
    "nubes",
    "lake",
    "lago",
    "laguna",
    "reservoir",
    "embalse",
    "river",
    "río",
    "waterfall",
    "cascada",
    "valley",
    "valle",
    "forest",
    "bosque",
    "peak",
    "pico",
    "summit",
    "coast",
    "costa",
    "beach",
    "playa",
    "cliff",
    "acantilado",
    "lighthouse",
    "faro",
    "natural park",
    "parque natural",
    "national park",
    "parque nacional",
    "snow",
    "nieve",
    "autumn",
    "otoño",
    "dehesa",
    "meadow",
    "pradera",
    "gorge",
    "garganta",
    "cañón",
    "hoces",
    # gallego, catalán, asturiano y términos de costa (vistos al probar en Costa da Morte)
    "cabo ",
    "cape ",
    "capes",
    "fervenza",
    "praia",
    "punta ",
    "miradoiro",
    "illa",
    "ría ",
    "seascape",
    "coastline",
    "sea stack",
    "mar de",
    "cala ",
    "platja",
    "salto de agua",
    "lagoa",
)


# Ojo con subcadenas: "aves" casaría con "waves" y "map" con "maple", por eso van en plural/completas
PALABRAS_EXCLUIR = (
    "interior",
    "portrait",
    "retrato",
    "people",
    "logos",
    "maps",
    "mapas",
    "diagrams",
    "coats of arms",
    "escudo",
    "museum",
    "museo",
    "food",
    "insects",
    "birds",
    "flowers",
    "plaques",
    "placas",
    "signs",
    "vehicles",
    "trains",
    "buses",
    "aircraft",
    "documents",
    "postage stamps",
    "paintings",
    # vistos en la primera ejecución real (Sierra de Madrid, oct-2026):
    "from space",
    "iss expedition",
    "aurora viewed",
    "earth at night",  # fotos de la ISS geolocalizadas
    "grand prix",
    "motorsport",
    "rail transport",
    "railway stations",
    "avant ",
    "animals",
    "mammals",
    "reptiles",
    "snakes",
    "coronella",
    "ciconia",
    "storks",
    "fungi",
    "mushrooms",
    "plants of",
    "churches",
    "iglesia",
    "chapels",
    "ermita",
    "plaza mayor",
    "streets",
    "calles",
    "festivals",
    "fiestas",
    "celebrations",
    "town halls",
    "casas consistoriales",
    "sculptures",
    "esculturas",
    "graffiti",
    "schools",
    "instituto",
    "education",
    "educación",
    "skiers",
    "esquiadores",
    "sports",
    "deportes",
    "train station",
    "stations",
    "estación de",
    "shearing",
    "esquileo",
    "factories",
    "fábricas",
    "industrial",
    "throne",
    "rooms",
    "salón",
    "salas",
    "halls",
    "ceilings",
    "techos",
    "furniture",
)


def consultar(params: dict) -> dict:
    """Llamada a la API de Commons con caché, maxlag y reintentos amables."""
    params = {"action": "query", "format": "json", "formatversion": 2, "maxlag": 5, **params}
    clave = "commons:" + json.dumps(params, sort_keys=True)
    datos = CACHE.leer(clave)
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
        CACHE.guardar(clave, datos)
        time.sleep(COMMONS_PAUSA_S)
        return datos
    raise RuntimeError("Commons no responde (demasiados reintentos)")


def texto_plano(v: str | None) -> str:
    return re.sub(r"\s+", " ", htmlmod.unescape(re.sub(r"<[^>]+>", "", v or ""))).strip()


def fecha_exif(v: str | None):
    m = re.search(r"(\d{4})[-:](\d{2})[-:](\d{2})[ T](\d{2}):(\d{2})", texto_plano(v))
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
        lote = pageids[i : i + 50]
        paginas: dict[int, dict] = {}
        params = {
            "pageids": "|".join(map(str, lote)),
            "prop": "imageinfo|categories",
            "iiprop": "url|user|extmetadata",
            "iiurlwidth": 500,
            "iiextmetadatafilter": "DateTimeOriginal|Artist|LicenseShortName|ObjectName",
            "cllimit": "max",
            "clshow": "!hidden",
        }
        cont: dict = {}
        while True:  # las categorías vienen paginadas con 'continue'
            datos = consultar({**params, **cont})
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
            filas.append(
                {
                    "id": pid,
                    "titulo": texto_plano(meta.get("ObjectName", {}).get("value"))
                    or (p["titulo"] or "").removeprefix("File:").rsplit(".", 1)[0],
                    "autor_cuenta": ii.get("user"),
                    "autor": texto_plano(meta.get("Artist", {}).get("value")) or ii.get("user"),
                    "licencia": texto_plano(meta.get("LicenseShortName", {}).get("value")),
                    "datetaken": fecha_exif(meta.get("DateTimeOriginal", {}).get("value")),
                    "url_m": ii.get("thumburl"),
                    "web": ii.get("descriptionurl"),
                    "categorias": p["cats"],
                }
            )
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
    # La calidad reconocida no basta: hay fotos de calidad de interiores (salón del trono del Alcázar)
    return paisaje and not excluir, calidad


def fotos_cerca(lat: float, lon: float, radio_m: int = 500) -> list[dict]:
    datos = consultar(
        {"list": "geosearch", "gscoord": f"{lat:.5f}|{lon:.5f}", "gsradius": radio_m, "gsnamespace": 6, "gslimit": 500}
    )
    return [
        g
        for g in datos.get("query", {}).get("geosearch", [])
        if re.search(r"\.(jpe?g|png|tiff?|webp)$", g["title"], re.I)
    ]


def galeria(cerca: list[dict], imagen_wd: str | None, maximo: int = 6) -> tuple[list[dict], int, list[int]]:
    """Fotos de paisaje con autor y licencia (primero la imagen de Wikidata), nº de autores y meses."""
    ids = [g["pageid"] for g in sorted(cerca, key=lambda g: g.get("dist", 0))[:50]]
    filas = detalles_commons(ids) if ids else []
    if imagen_wd:
        d = consultar(
            {
                "titles": f"File:{imagen_wd}",
                "prop": "imageinfo|categories",
                "iiprop": "url|user|extmetadata",
                "iiurlwidth": 500,
                "iiextmetadatafilter": "DateTimeOriginal|Artist|LicenseShortName|ObjectName",
                "cllimit": "max",
                "clshow": "!hidden",
            }
        )
        for p in d.get("query", {}).get("pages", []):
            ii = (p.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata") or {}
            if ii.get("thumburl") and isinstance(meta, dict):
                filas.insert(
                    0,
                    {
                        "id": p.get("pageid"),
                        "titulo": imagen_wd.rsplit(".", 1)[0],
                        "autor_cuenta": ii.get("user"),
                        "autor": texto_plano(meta.get("Artist", {}).get("value")) or ii.get("user"),
                        "licencia": texto_plano(meta.get("LicenseShortName", {}).get("value")),
                        "datetaken": fecha_exif(meta.get("DateTimeOriginal", {}).get("value")),
                        "url_m": ii.get("thumburl"),
                        "web": ii.get("descriptionurl"),
                        "categorias": ["landscape"],
                        "wikidata": True,
                    },
                )
    df = pd.DataFrame(filas)
    if df.empty:
        return [], 0, [0] * 12
    df["owner"] = df["autor_cuenta"].fillna(df["autor"])
    df["paisaje"] = df["categorias"].map(lambda c: clasificar_paisaje(c)[0])
    meses = pd.to_datetime(df["datetaken"], errors="coerce").dropna().dt.month.value_counts()
    de_wd = df["wikidata"].fillna(False).astype(bool) if "wikidata" in df else pd.Series(False, index=df.index)
    elegidas = pd.concat([df[de_wd], df[df.paisaje]]).drop_duplicates("id")
    elegidas = pd.concat([elegidas.drop_duplicates("owner"), elegidas]).drop_duplicates("id").head(maximo)
    fotos = [
        {
            "url": r.url_m,
            "enlace": r.web,
            "autor": str(r.autor or r.owner or "")[:80],
            "licencia": r.licencia or "",
            "titulo": str(r.titulo or "")[:120],
            "fecha": None if pd.isna(r.datetaken) else pd.Timestamp(r.datetaken).strftime("%Y-%m-%d"),
        }
        for r in elegidas.itertuples()
        if r.url_m and (r.licencia or getattr(r, "wikidata", False) is True)
    ]
    return fotos, int(df.owner.nunique()), [int(meses.get(m, 0)) for m in range(1, 13)]
