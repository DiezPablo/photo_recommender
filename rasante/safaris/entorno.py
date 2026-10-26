"""Lo que rodea a cada parque: ficha de Wikidata, clima de cada mes (Open-Meteo, ERA5) y alojamientos de OSM."""

from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from datetime import date
from urllib.parse import unquote

import requests

from rasante.comun.cache import CacheJson
from rasante.comun.red import sesion
from rasante.safaris.practico import url_web
from rasante.spots.commons import consultar, texto_plano

CACHE = CacheJson(prefijo="safaris_", max_edad_s=25 * 86400)
_SESION = sesion()
WIKIDATA = "https://query.wikidata.org/sparql"
ARCHIVO = "https://archive-api.open-meteo.com/v1/archive"
# Dos años: suficiente para la forma del año. Open-Meteo cuenta una llamada por cada 14 días pedidos (~52 por
# parque): con la pausa entre parques no se pasa del límite por minuto ni por hora (5000).
ANOS_CLIMA = (2023, 2024)
PAUSA_CLIMA_S = 8
OVERPASS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
)
ALOJAMIENTO = {
    "hotel": "hotel",
    "guest_house": "casa de huéspedes",
    "camp_site": "campamento",
    "chalet": "cabaña",
    "hostel": "albergue",
    "motel": "motel",
    "wilderness_hut": "refugio",
    "apartment": "apartamento",
}


def _cache(clave: str, pedir):
    guardado = CACHE.leer(clave)
    if guardado is not None:
        return guardado
    datos = pedir()
    CACHE.guardar(clave, datos)
    return datos


def wikidata(qids: list[str]) -> dict[str, dict]:
    """Foto, web oficial y artículo de Wikipedia en español de cada parque."""
    valores = " ".join(f"wd:{q}" for q in qids)
    consulta = f"""SELECT ?x ?img ?web ?es WHERE {{
      VALUES ?x {{ {valores} }}
      OPTIONAL {{ ?x wdt:P18 ?img }}
      OPTIONAL {{ ?x wdt:P856 ?web }}
      OPTIONAL {{ ?es schema:about ?x; schema:isPartOf <https://es.wikipedia.org/> }}
    }}"""

    def pedir():
        r = _SESION.get(WIKIDATA, params={"query": consulta, "format": "json"}, timeout=120)
        r.raise_for_status()
        return r.json()["results"]["bindings"]

    salida: dict[str, dict] = {}
    for b in _cache("wd:" + consulta, pedir):
        q = b["x"]["value"].rsplit("/", 1)[1]
        s = salida.setdefault(q, {})
        for campo in ("img", "web", "es"):
            if campo in b and campo not in s:  # si hay varios valores, el primero
                s[campo] = b[campo]["value"]
    return salida


def fotos_commons(urls: list[str]) -> dict[str, dict]:
    """Miniatura de 960 px, autor y licencia de cada imagen de Wikidata (URL Special:FilePath)."""
    titulos = {u: "File:" + unquote(u.rsplit("/", 1)[1]) for u in urls}
    lista = sorted(set(titulos.values()))
    info: dict[str, dict] = {}
    for i in range(0, len(lista), 50):
        d = consultar(
            {
                "titles": "|".join(lista[i : i + 50]),
                "prop": "imageinfo",
                "iiprop": "url|user|extmetadata",
                "iiurlwidth": 960,
                "iiextmetadatafilter": "Artist|LicenseShortName",
            }
        )
        alias = {n["to"]: n["from"] for n in d.get("query", {}).get("normalized", [])}
        for p in d.get("query", {}).get("pages", []):
            ii = (p.get("imageinfo") or [None])[0]
            if not ii or not ii.get("thumburl"):
                continue
            meta = ii.get("extmetadata", {})
            info[alias.get(p["title"], p["title"])] = {
                "url": ii["thumburl"].split("?")[0],
                "web": ii.get("descriptionurl"),
                "autor": texto_plano(meta.get("Artist", {}).get("value")) or ii.get("user"),
                "licencia": texto_plano(meta.get("LicenseShortName", {}).get("value")),
            }
    return {u: info[t] for u, t in titulos.items() if t in info}


def clima(lat: float, lon: float) -> dict:
    """Lluvia media (mm) y máxima media (°C) de cada mes con ERA5 (Open-Meteo, sin clave)."""
    params = {
        "latitude": round(lat, 2),
        "longitude": round(lon, 2),
        "start_date": f"{ANOS_CLIMA[0]}-01-01",
        "end_date": f"{ANOS_CLIMA[1]}-12-31",
        "daily": "precipitation_sum,temperature_2m_max",
        "timezone": "UTC",
    }

    def pedir():
        for intento in range(3):
            time.sleep(PAUSA_CLIMA_S)
            try:
                r = _SESION.get(ARCHIVO, params=params, timeout=120)
            except (requests.ConnectionError, requests.Timeout):
                time.sleep(10 * (intento + 1))
                continue
            if r.status_code == 429:  # límite por minuto u hora: se espera un poco; si sigue, sin clima
                time.sleep(30 * (intento + 1))
                continue
            r.raise_for_status()
            return r.json()["daily"]
        raise requests.ConnectionError("Open-Meteo no responde")

    d = _cache("clima:" + json.dumps(params, sort_keys=True), pedir)
    lluvia, tmax = defaultdict(list), defaultdict(list)
    for t, p, x in zip(d["time"], d["precipitation_sum"], d["temperature_2m_max"], strict=True):
        f = date.fromisoformat(t)
        if p is not None:
            lluvia[(f.year, f.month)].append(p)
        if x is not None:
            tmax[f.month].append(x)
    anos = ANOS_CLIMA[1] - ANOS_CLIMA[0] + 1
    return {
        "lluvia_mm": [
            round(sum(sum(lluvia[(a, m)]) for a in range(ANOS_CLIMA[0], ANOS_CLIMA[1] + 1)) / anos)
            for m in range(1, 13)
        ],
        "tmax": [round(sum(tmax[m]) / len(tmax[m])) if tmax[m] else None for m in range(1, 13)],
    }


def _nombre_util(nombre: str) -> bool:
    """Fuera los códigos de acampada de travesía («12», «4R1 - Ribbon Lake West»): no son alojamientos a reservar."""
    codigo = re.match(r"^([A-Z0-9]{1,4})(\s+-\s+.*)?$", nombre.strip())
    return not (codigo and any(c.isdigit() for c in codigo.group(1)))


def alojamientos(lat: float, lon: float, radio_km: float, maximo: int = 30) -> list[dict]:
    """Lodges, campamentos y hoteles con nombre de OSM dentro del parque o a menos de 15 km de su zona."""
    tipos = "|".join(ALOJAMIENTO)
    radio_m = int((radio_km + 15) * 1000)
    consulta = (
        f'[out:json][timeout:120];nwr["tourism"~"^({tipos})$"]["name"](around:{radio_m},{lat},{lon});out center tags;'
    )

    def pedir():
        time.sleep(3)  # una consulta tras otra: los espejos públicos piden no saturarlos
        for intento in range(3):
            for url in OVERPASS:
                try:
                    r = _SESION.post(url, data={"data": consulta}, timeout=90)
                    r.raise_for_status()
                    return r.json()
                except (requests.RequestException, ValueError):
                    continue
            time.sleep(20 * (intento + 1))
        raise requests.ConnectionError("Overpass no responde")

    datos = _cache("osm:" + consulta, pedir)
    salida = []
    for e in datos.get("elements", []):
        t = e.get("tags", {})
        if not _nombre_util(t["name"]):
            continue
        la = e.get("lat") or e.get("center", {}).get("lat")
        lo = e.get("lon") or e.get("center", {}).get("lon")
        if la is None:
            continue
        salida.append(
            {
                "nombre": t.get("name:es") or t.get("name:en") or t["name"],
                "tipo": ALOJAMIENTO.get(t.get("tourism"), "alojamiento"),
                "lat": round(la, 5),
                "lon": round(lo, 5),
                "web": url_web(t.get("website") or t.get("contact:website") or t.get("url")),
                "telefono": t.get("phone") or t.get("contact:phone"),
                "estrellas": t.get("stars"),
                "osm": f"{e['type']}/{e['id']}",
            }
        )
    # primero los que tienen web (se puede reservar directamente), luego por nombre
    salida.sort(key=lambda a: (a["web"] is None, a["nombre"].lower()))
    return salida[:maximo]
