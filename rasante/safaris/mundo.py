"""Todos los parques del mundo donde se puede ver fauna: candidatos de Wikidata cribados con GBIF.

1. Candidatos (Wikidata): parques nacionales (y sus subclases), reservas de caza, refugios y reservas de fauna,
   áreas de gestión de fauna, áreas de conservación, reservas de la biosfera y, si miden ≥ 100 km², áreas
   protegidas y reservas naturales genéricas (así entran las conservancies de Kenia o las reservas privadas de
   Sudáfrica sin colar miles de reservas pequeñas). ~9500 candidatos.
2. Cribado (GBIF, una petición por candidato): mamíferos observados por personas o cámaras trampa (no
   ejemplares de museo) desde 2010 en la zona del parque (un círculo con su superficie). Se queda con los que tienen al menos `MIN_ESPECIES` especies y `MIN_OBS` observaciones.
   La misma petición da las especies con más observaciones y los meses.
3. Se quitan duplicados (el mismo parque como parque nacional y reserva de la biosfera).

Es caro la primera vez (horas) y se guarda en caché: las siguientes ejecuciones solo piden lo nuevo.
"""

from __future__ import annotations

import math
import re
import time
import unicodedata

import requests

from rasante.comun.cache import CacheJson
from rasante.comun.red import sesion

WIKIDATA = "https://query.wikidata.org/sparql"
GBIF = "https://api.gbif.org/v1/occurrence/search"
CACHE = CacheJson(prefijo="mundo_", max_edad_s=80 * 86400)  # los parques y su fauna cambian despacio
_SESION = sesion()

CLASES_TODAS = {
    "Q1714375": "reserva de caza",
    "Q1377575": "refugio de fauna",
    "Q76163442": "refugio de fauna",
    "Q20268591": "reserva de fauna",
    "Q8001309": "área de gestión de fauna",
    "Q936257": "área de conservación",
    "Q158454": "reserva de la biosfera",
}
CLASES_GRANDES = {"Q473972": "área protegida", "Q179049": "reserva natural"}
AREA_MIN_GRANDES_M2 = 100e6
MIN_ESPECIES, MIN_OBS = 10, 50
RADIO_MIN_KM, RADIO_MAX_KM = 4.0, 80.0
RADIO_SIN_AREA_KM = {"parque nacional": 15.0}
DESDE_ANO = 2010
MAMIFEROS, AVES = 359, 212
# Animales domésticos que no pintan nada en un safari (nombres científicos de GBIF)
DOMESTICOS = {
    "Equus caballus",
    "Equus asinus",
    "Bos taurus",
    "Bos indicus",
    "Ovis aries",
    "Capra hircus",
    "Sus domesticus",
    "Felis catus",
    "Canis familiaris",
    "Homo sapiens",
    "Bubalus bubalis",
    "Camelus dromedarius",
    "Lama glama",
    "Cavia porcellus",
    "Oryctolagus cuniculus domesticus",
}
# GBIF cuelga los perros de la especie Canis lupus: en muchos parques el «lobo» son perros
SUBESPECIE_DOMESTICA = {5219173: 6164210}


def _sparql(consulta: str) -> list[dict]:
    clave = "sparql:" + consulta
    guardado = CACHE.leer(clave)
    if guardado is not None:
        return guardado
    for intento in range(5):
        try:
            r = _SESION.get(WIKIDATA, params={"query": consulta, "format": "json"}, timeout=180)
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(15 * (intento + 1))
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(int(r.headers.get("Retry-After", 0) or 30 * (intento + 1)))
            continue
        r.raise_for_status()
        filas = r.json()["results"]["bindings"]
        CACHE.guardar(clave, filas)
        time.sleep(2)
        return filas
    raise requests.ConnectionError("Wikidata no responde")


def _qid(uri: str) -> str:
    return uri.rsplit("/", 1)[1]


def _punto(wkt: str) -> tuple[float, float] | None:
    m = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", wkt)
    return (float(m.group(2)), float(m.group(1))) if m else None


def candidatos() -> dict[str, dict]:
    """{qid: {lat, lon, area_m2, pais (qid), clase}} de todas las clases; si hay varias coordenadas, la primera."""
    salida: dict[str, dict] = {}

    def anadir(filas, clase):
        for b in filas:
            punto = _punto(b["c"]["value"])
            if punto is None:
                continue
            # un parque nacional que además es reserva de la biosfera conserva la clase del primero (parque)
            x = salida.setdefault(
                _qid(b["x"]["value"]),
                {"lat": punto[0], "lon": punto[1], "area_m2": None, "pais": None, "clase": clase},
            )
            if "a" in b and x["area_m2"] is None:
                x["area_m2"] = float(b["a"]["value"])
            if "p" in b and x["pais"] is None:
                x["pais"] = _qid(b["p"]["value"])

    opcional = "OPTIONAL { ?x p:P2046/psn:P2046/wikibase:quantityAmount ?a } OPTIONAL { ?x wdt:P17 ?p }"
    anadir(
        _sparql(f"SELECT ?x ?c ?a ?p WHERE {{ ?x wdt:P31/wdt:P279* wd:Q46169; wdt:P625 ?c. {opcional} }}"),
        "parque nacional",
    )
    for q, clase in CLASES_TODAS.items():
        anadir(_sparql(f"SELECT ?x ?c ?a ?p WHERE {{ ?x wdt:P31 wd:{q}; wdt:P625 ?c. {opcional} }}"), clase)
    for q, clase in CLASES_GRANDES.items():
        filas = _sparql(
            f"SELECT ?x ?c ?a ?p WHERE {{ ?x wdt:P31 wd:{q}; wdt:P625 ?c; "
            f"p:P2046/psn:P2046/wikibase:quantityAmount ?a. FILTER(?a >= {AREA_MIN_GRANDES_M2:.0f}) "
            "OPTIONAL { ?x wdt:P17 ?p } }"
        )
        anadir(filas, clase)
    return salida


def radio_km(area_m2: float | None, clase: str) -> float:
    if not area_m2:
        return RADIO_SIN_AREA_KM.get(clase, 8.0)
    r = math.sqrt(area_m2 / 1e6 / math.pi)
    return round(min(RADIO_MAX_KM, max(RADIO_MIN_KM, r)), 1)


def caja(lat: float, lon: float, r_km: float) -> dict:
    dlat = r_km / 111.0
    dlon = r_km / (111.0 * max(0.2, math.cos(math.radians(lat))))
    return {
        "decimalLatitude": f"{max(-90, lat - dlat):.4f},{min(90, lat + dlat):.4f}",
        "decimalLongitude": f"{max(-180, lon - dlon):.4f},{min(180, lon + dlon):.4f}",
    }


def conteo_taxon(lat: float, lon: float, r_km: float, taxon: int) -> int:
    """Observaciones de un taxón concreto en la zona (para restar los perros del «lobo»)."""
    params = {
        **caja(lat, lon, r_km),
        "taxonKey": taxon,
        "year": f"{DESDE_ANO},2030",
        "occurrenceStatus": "PRESENT",
        "hasGeospatialIssue": "false",
        "basisOfRecord": ["HUMAN_OBSERVATION", "MACHINE_OBSERVATION"],
        "limit": 0,
    }
    clave = "gbif-n:" + repr(sorted(params.items()))
    n = CACHE.leer(clave)
    if n is None:
        r = _SESION.get(GBIF, params=params, timeout=60)
        r.raise_for_status()
        n = r.json().get("count", 0)
        CACHE.guardar(clave, n)
    return n


def gbif(lat: float, lon: float, r_km: float, clase_gbif: int, n: int = 200) -> dict:
    """Observaciones, especies (clave, n) y meses de una clase (mamíferos o aves) en la zona."""
    params = {
        **caja(lat, lon, r_km),
        "classKey": clase_gbif,
        "year": f"{DESDE_ANO},2030",
        "occurrenceStatus": "PRESENT",
        "hasGeospatialIssue": "false",
        # lo que ve la gente (observaciones y cámaras trampa), no los ejemplares de museo
        "basisOfRecord": ["HUMAN_OBSERVATION", "MACHINE_OBSERVATION"],
        "limit": 0,
        "facet": ["speciesKey", "month"],
        "speciesKey.facetLimit": n,
        "month.facetLimit": 12,
    }
    clave = "gbif:" + repr(sorted(params.items()))
    guardado = CACHE.leer(clave)
    if guardado is None:
        for intento in range(6):
            try:
                r = _SESION.get(GBIF, params=params, timeout=60)
            except (requests.ConnectionError, requests.Timeout):
                time.sleep(5 * (intento + 1))
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(int(r.headers.get("Retry-After", 0) or 10 * (intento + 1)))
                continue
            r.raise_for_status()
            d = r.json()
            facetas = {f["field"]: f["counts"] for f in d.get("facets", [])}
            meses = [0] * 12
            for m in facetas.get("MONTH", []):
                meses[int(m["name"]) - 1] = m["count"]
            guardado = {
                "obs": d.get("count", 0),
                "especies": [[int(e["name"]), e["count"]] for e in facetas.get("SPECIES_KEY", [])],
                "meses": meses,
            }
            CACHE.guardar(clave, guardado)
            break
        else:
            raise requests.ConnectionError("GBIF no responde")
    return guardado


def slug(texto: str) -> str:
    # sin tildes, y cualquier otro signo (guiones largos incluidos) como separador
    t = "".join(c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60]


def detalles(qids: list[str], lote: int = 250) -> dict[str, dict]:
    """Nombre (es/en), foto, web, Wikipedia en español, categoría UICN, Patrimonio Mundial y WDPA."""
    salida: dict[str, dict] = {}
    for i in range(0, len(qids), lote):
        valores = " ".join(f"wd:{q}" for q in qids[i : i + lote])
        filas = _sparql(
            f"""SELECT ?x ?es ?en ?img ?web ?wiki ?iucnl ?wdpa ?unesco WHERE {{
              VALUES ?x {{ {valores} }}
              OPTIONAL {{ ?x rdfs:label ?es FILTER(lang(?es) = "es") }}
              OPTIONAL {{ ?x rdfs:label ?en FILTER(lang(?en) = "en") }}
              OPTIONAL {{ ?x wdt:P18 ?img }}
              OPTIONAL {{ ?x wdt:P856 ?web }}
              OPTIONAL {{ ?wiki schema:about ?x; schema:isPartOf <https://es.wikipedia.org/> }}
              OPTIONAL {{ ?x wdt:P814 ?iucn. ?iucn rdfs:label ?iucnl FILTER(lang(?iucnl) = "es") }}
              OPTIONAL {{ ?x wdt:P809 ?wdpa }}
              OPTIONAL {{ ?x wdt:P1435 wd:Q9259. BIND(true AS ?unesco) }}
            }}"""
        )
        for b in filas:
            d = salida.setdefault(_qid(b["x"]["value"]), {})
            for campo in ("es", "en", "img", "web", "wiki", "iucnl", "wdpa", "unesco"):
                if campo in b and campo not in d:
                    d[campo] = b[campo]["value"]
    return salida


def paises(qids: list[str]) -> dict[str, dict]:
    """Nombre en español, continente, moneda e idiomas oficiales de cada país."""
    valores = " ".join(f"wd:{q}" for q in sorted(set(qids)))
    filas = _sparql(
        f"""SELECT ?p ?n ?cont ?mon ?idi WHERE {{
          VALUES ?p {{ {valores} }}
          OPTIONAL {{ ?p rdfs:label ?n FILTER(lang(?n) = "es") }}
          OPTIONAL {{ ?p wdt:P30 ?c. ?c rdfs:label ?cont FILTER(lang(?cont) = "es") }}
          OPTIONAL {{ ?p wdt:P38 ?m. ?m rdfs:label ?mon FILTER(lang(?mon) = "es") }}
          OPTIONAL {{ ?p wdt:P37 ?i. ?i rdfs:label ?idi FILTER(lang(?idi) = "es") }}
        }}"""
    )
    salida: dict[str, dict] = {}
    for b in filas:
        d = salida.setdefault(_qid(b["p"]["value"]), {"idiomas": []})
        for campo in ("n", "cont", "mon"):
            if campo in b and campo not in d:
                d[campo] = b[campo]["value"]
        if "idi" in b and b["idi"]["value"] not in d["idiomas"]:
            d["idiomas"].append(b["idi"]["value"])
    return salida


CONTINENTE = {
    "África": "África",
    "Asia": "Asia",
    "Europa": "Europa",
    "América del Norte": "América",
    "América del Sur": "América",
    "Norteamérica": "América",
    "Sudamérica": "América",
    "América": "América",
    "Oceanía": "Oceanía",
    "Australia": "Oceanía",
    "Antártida": "Antártida",
}
