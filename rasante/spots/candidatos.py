"""Candidatos a spot en toda España: Wikidata (lugares con foto de tipos fotogénicos) y OpenStreetMap
(miradores, cumbres, cascadas, faros…), fusionados cuando están a menos de 400 m."""

from __future__ import annotations

import re
import time

import numpy as np
import pandas as pd
import requests

from rasante.comun.red import sesion

from .commons import CACHE

SESION = sesion()


# Overpass tiene varios espejos públicos; si uno falla o corta la conexión probamos el siguiente
OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)


RADIO_TIERRA_M = 6_371_000


WIKIDATA = "https://query.wikidata.org/sparql"


# Bloques para Overpass (lon0, lat0, lon1, lat1): península + Baleares en 2°×2° y Canarias aparte
# Bloques para Overpass (lon0, lat0, lon1, lat1): península y Baleares en 4°×4° y Canarias aparte.
# Una sola consulta por bloque con todos los tipos (con una por tipo y bloque de 2° tardaba 2 h).
BLOQUES = [(x, y, x + 4, y + 4) for x in range(-10, 5, 4) for y in (36, 40)] + [(-18.3, 27.5, -13.3, 29.5)]


# Tipos de Wikidata (QID → tipo de spot)
TIPOS_WD = {
    "Q8502": "cumbre",
    "Q207326": "cumbre",
    "Q23397": "lago",
    "Q131681": "embalse",
    "Q40080": "playa",
    "Q34038": "cascada",
    "Q6017969": "mirador",
    "Q185113": "cabo",
    "Q39715": "faro",
    "Q150784": "cañón",
    "Q107679": "acantilado",
}


FILTROS_OSM = [
    ('node["tourism"="viewpoint"]["name"]', "mirador"),
    ('node["natural"="peak"]["wikidata"]', "cumbre"),
    ('node["waterway"="waterfall"]["name"]', "cascada"),
    ('node["man_made"="lighthouse"]', "faro"),
    ('node["natural"="cape"]["name"]', "cabo"),
    ('way["natural"="cliff"]["name"]', "acantilado"),
]


def _sparql(consulta: str) -> list[dict]:
    clave = "wd:" + consulta
    datos = CACHE.leer(clave)
    if datos is not None:
        return datos
    for intento in range(6):
        try:
            r = SESION.get(
                WIKIDATA,
                params={"query": consulta, "format": "json"},
                timeout=120,
                headers={"Accept": "application/sparql-results+json"},
            )
        except requests.RequestException:
            time.sleep(10 * (intento + 1))
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(int(r.headers.get("Retry-After", 0) or 15 * (intento + 1)))
            continue
        r.raise_for_status()
        filas = r.json()["results"]["bindings"]
        CACHE.guardar(clave, filas)
        time.sleep(1)
        return filas
    print("      Wikidata no responde; sigo sin esa consulta")
    return []


def candidatos_wikidata() -> pd.DataFrame:
    filas = []
    for qid, tipo in TIPOS_WD.items():
        consulta = f"""SELECT ?item ?lab ?coord ?img ?links WHERE {{
  ?item wdt:P31 wd:{qid}; wdt:P17 wd:Q29; wdt:P625 ?coord; wdt:P18 ?img; wikibase:sitelinks ?links .
  OPTIONAL {{ ?item rdfs:label ?lab FILTER(LANG(?lab) = "es") }}
}}"""
        res = _sparql(consulta)
        for b in res:
            m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", b["coord"]["value"])
            if not m:
                continue
            filas.append(
                {
                    "nombre": b.get("lab", {}).get("value"),
                    "lon": float(m.group(1)),
                    "lat": float(m.group(2)),
                    "tipo": tipo,
                    "wikidata": b["item"]["value"].rsplit("/", 1)[-1],
                    "imagen": b["img"]["value"].rsplit("/", 1)[-1],
                    "sitelinks": int(b["links"]["value"]),
                    "fuente": "wikidata",
                }
            )
        print(f"      Wikidata {tipo}: {len(res)}", flush=True)
    df = pd.DataFrame(filas)
    return df.drop_duplicates("wikidata") if not df.empty else df


def _tipo_osm(t: dict) -> str | None:
    if t.get("tourism") == "viewpoint":
        return "mirador"
    if t.get("natural") == "peak":
        return "cumbre"
    if t.get("waterway") == "waterfall":
        return "cascada"
    if t.get("man_made") == "lighthouse":
        return "faro"
    if t.get("natural") == "cape":
        return "cabo"
    if t.get("natural") == "cliff":
        return "acantilado"
    return None


def candidatos_osm() -> pd.DataFrame:
    filas = []
    for x0, y0, x1, y1 in BLOQUES:
        caja = f"({y0},{x0},{y1},{x1})"
        cuerpo = "".join(f"{filtro}{caja};" for filtro, _ in FILTROS_OSM)
        consulta = f"[out:json][timeout:300];({cuerpo});out center tags;"
        datos = CACHE.leer(consulta)
        if datos is None:
            t = time.time()
            for intento in range(3):
                for url in OVERPASS_URLS:
                    try:
                        r = SESION.post(url, data={"data": consulta}, timeout=360)
                        r.raise_for_status()
                        datos = r.json()
                        break
                    except (requests.RequestException, ValueError):
                        continue
                if datos is not None:
                    break
                time.sleep(30 * (intento + 1))
            if datos is None:
                print(f"      Overpass no responde para el bloque {caja}")
                continue
            CACHE.guardar(consulta, datos)
            print(
                f"      bloque {caja}: {len(datos.get('elements', []))} elementos en {time.time() - t:.0f} s",
                flush=True,
            )
            time.sleep(5)
        for e in datos.get("elements", []):
            lat = e.get("lat") or e.get("center", {}).get("lat")
            lon = e.get("lon") or e.get("center", {}).get("lon")
            t = e.get("tags", {})
            tipo = _tipo_osm(t)
            if lat is None or tipo is None:
                continue
            filas.append(
                {
                    "nombre": t.get("name:es") or t.get("name"),
                    "lat": lat,
                    "lon": lon,
                    "tipo": tipo,
                    "wikidata": t.get("wikidata"),
                    "imagen": None,
                    "sitelinks": 0,
                    "direccion_vista": t.get("direction"),
                    "ele": t.get("ele"),
                    "fuente": "osm",
                }
            )
    print(f"      OSM: {len(filas)} elementos", flush=True)
    return pd.DataFrame(filas)


def fusionar(wd: pd.DataFrame, osm: pd.DataFrame, radio_m: float = 400) -> pd.DataFrame:
    """Une Wikidata y OSM: mismo Wikidata o a menos de 400 m y mismo tipo → un único candidato."""
    df = pd.concat([wd, osm], ignore_index=True)
    df["prioridad"] = (df.fuente == "wikidata").astype(int) * 2 + df.nombre.notna().astype(int)
    df = df.sort_values("prioridad", ascending=False)
    df = pd.concat([df[df.wikidata.isna()], df[df.wikidata.notna()].drop_duplicates("wikidata")])
    df = df.sort_values("prioridad", ascending=False).reset_index(drop=True)
    coords = np.radians(df[["lat", "lon"]].to_numpy())
    from sklearn.neighbors import BallTree

    arbol = BallTree(coords, metric="haversine")
    vecinos = arbol.query_radius(coords, r=radio_m / RADIO_TIERRA_M)
    absorbido = np.zeros(len(df), dtype=bool)
    for i, vs in enumerate(vecinos):
        if absorbido[i]:
            continue
        for j in vs:
            if j > i and not absorbido[j]:
                absorbido[j] = True
                for c in ("direccion_vista", "ele", "imagen", "wikidata"):
                    if pd.isna(df.at[i, c]) and not pd.isna(df.at[j, c]):
                        df.at[i, c] = df.at[j, c]
    return df[~absorbido].drop(columns="prioridad").reset_index(drop=True)
