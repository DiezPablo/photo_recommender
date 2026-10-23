#!/usr/bin/env python3
"""
descubrir_espana.py — Spots de fotografía de paisaje en toda España.

Candidatos (sin clave de API):
  - Wikidata: lugares con foto (P18) y coordenadas en España de tipos fotogénicos (montañas, lagos,
    embalses, playas, cascadas, miradores, cabos, faros, cañones, acantilados). Los "sitelinks"
    (artículos en Wikipedia) miden lo conocido que es.
  - OpenStreetMap (Overpass, por bloques): miradores con nombre, cumbres con Wikidata, cascadas,
    faros, cabos y acantilados con nombre.
Popularidad: número de fotos geolocalizadas en Wikimedia Commons a menos de 500 m.
Selección: los mejores de cada provincia (para cubrir todo el país) y el resto por puntuación nacional.
Para cada spot elegido: galería de Commons (autor y licencia), horizonte del terreno (horizonte.py),
contaminación lumínica (contaminacion.py), provincia y comunidad autónoma.

El primer cálculo hace ~13 000 peticiones a Commons (≈ 2 h en GitHub Actions); todo queda en
cache/ y las ejecuciones siguientes solo piden lo nuevo. Con --minutos se corta a tiempo y la
siguiente ejecución continúa.

Uso:
  python descubrir_espana.py --salida public/datos             # ~1500 spots
  python descubrir_espana.py --total 300 --por-provincia 4     # prueba rápida
"""
from __future__ import annotations

import argparse
import json
import math
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

import descubrir_spots as D
import horizonte
from comun import USER_AGENT, escribir_json, id_spot
from contaminacion import contaminacion

WIKIDATA = "https://query.wikidata.org/sparql"
PROVINCIAS = Path(__file__).parent / "datos_base" / "provincias.geojson"
# Bloques para Overpass (lon0, lat0, lon1, lat1): península + Baleares en 2°×2° y Canarias aparte
BLOQUES = [(x, y, x + 2, y + 2) for x in range(-10, 5, 2) for y in range(36, 44, 2)] + [(-18.3, 27.5, -13.3, 29.5)]
# Tipos de Wikidata (QID → tipo de spot)
TIPOS_WD = {
    "Q8502": "cumbre", "Q207326": "cumbre", "Q23397": "lago", "Q131681": "embalse", "Q40080": "playa",
    "Q34038": "cascada", "Q6017969": "mirador", "Q185113": "cabo", "Q39715": "faro", "Q150784": "cañón",
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
PESO_TIPO = {"mirador": 1.0, "cabo": 0.8, "faro": 0.6, "acantilado": 0.6, "cumbre": 0.5, "lago": 0.6,
             "cascada": 0.4, "cañón": 0.6, "playa": 0.3, "embalse": 0.3}
SESION = requests.Session()
SESION.headers["User-Agent"] = USER_AGENT


# ------------------------------------------------------------ provincias ----
class Provincias:
    def __init__(self, ruta: Path = PROVINCIAS):
        fs = json.loads(ruta.read_text())["features"]
        self.geoms = [shape(f["geometry"]) for f in fs]
        self.props = [f["properties"] for f in fs]
        self.arbol = STRtree(self.geoms)

    def de(self, lat: float, lon: float) -> dict | None:
        p = Point(lon, lat)
        for i in self.arbol.query(p):
            if self.geoms[i].contains(p):
                return self.props[i]
        # en la costa el polígono simplificado puede quedarse corto: la provincia a menos de 1,5 km
        cerca = self.arbol.query(p.buffer(0.015))
        if len(cerca):
            i = min(cerca, key=lambda j: self.geoms[j].distance(p))
            return self.props[i]
        return None


# ------------------------------------------------------------- Wikidata ----
def _sparql(consulta: str) -> list[dict]:
    clave = "wd:" + consulta
    datos = D._cache_get(clave)
    if datos is not None:
        return datos
    for intento in range(6):
        try:
            r = SESION.get(WIKIDATA, params={"query": consulta, "format": "json"}, timeout=120,
                           headers={"Accept": "application/sparql-results+json"})
        except requests.RequestException:
            time.sleep(10 * (intento + 1))
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(int(r.headers.get("Retry-After", 0) or 15 * (intento + 1)))
            continue
        r.raise_for_status()
        filas = r.json()["results"]["bindings"]
        D._cache_set(clave, filas)
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
            filas.append({"nombre": b.get("lab", {}).get("value"), "lon": float(m.group(1)), "lat": float(m.group(2)),
                          "tipo": tipo, "wikidata": b["item"]["value"].rsplit("/", 1)[-1],
                          "imagen": b["img"]["value"].rsplit("/", 1)[-1], "sitelinks": int(b["links"]["value"]),
                          "fuente": "wikidata"})
        print(f"      Wikidata {tipo}: {len(res)}", flush=True)
    df = pd.DataFrame(filas)
    return df.drop_duplicates("wikidata") if not df.empty else df


# ----------------------------------------------------------------- OSM ----
def candidatos_osm() -> pd.DataFrame:
    filas = []
    for x0, y0, x1, y1 in BLOQUES:
        caja = f"({y0},{x0},{y1},{x1})"
        for filtro, tipo in FILTROS_OSM:
            consulta = f"[out:json][timeout:180];({filtro}{caja};);out center tags;"
            datos = D._cache_get(consulta)
            if datos is None:
                for url in D.OVERPASS_URLS:
                    try:
                        r = SESION.post(url, data={"data": consulta}, timeout=240)
                        r.raise_for_status()
                        datos = r.json()
                        break
                    except (requests.RequestException, ValueError):
                        continue
                if datos is None:
                    print(f"      Overpass no responde para {tipo} {caja}")
                    continue
                D._cache_set(consulta, datos)
                time.sleep(2)
            for e in datos.get("elements", []):
                lat = e.get("lat") or e.get("center", {}).get("lat")
                lon = e.get("lon") or e.get("center", {}).get("lon")
                if lat is None:
                    continue
                t = e.get("tags", {})
                filas.append({"nombre": t.get("name:es") or t.get("name"), "lat": lat, "lon": lon, "tipo": tipo,
                              "wikidata": t.get("wikidata"), "imagen": None, "sitelinks": 0,
                              "direccion_vista": t.get("direction"), "ele": t.get("ele"), "fuente": "osm"})
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
    vecinos = arbol.query_radius(coords, r=radio_m / D.RADIO_TIERRA_M)
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


# -------------------------------------------------------------- Commons ----
def fotos_cerca(lat: float, lon: float, radio_m: int = 500) -> list[dict]:
    datos = D._commons({"list": "geosearch", "gscoord": f"{lat:.5f}|{lon:.5f}", "gsradius": radio_m,
                        "gsnamespace": 6, "gslimit": 500})
    return [g for g in datos.get("query", {}).get("geosearch", [])
            if re.search(r"\.(jpe?g|png|tiff?|webp)$", g["title"], re.I)]


def galeria(cerca: list[dict], imagen_wd: str | None, maximo: int = 6) -> tuple[list[dict], int, list[int]]:
    """Fotos de paisaje con autor y licencia (primero la imagen de Wikidata), nº de autores y meses."""
    ids = [g["pageid"] for g in sorted(cerca, key=lambda g: g.get("dist", 0))[:50]]
    filas = D.detalles_commons(ids) if ids else []
    if imagen_wd:
        d = D._commons({"titles": f"File:{imagen_wd}", "prop": "imageinfo|categories",
                        "iiprop": "url|user|extmetadata", "iiurlwidth": 500,
                        "iiextmetadatafilter": "DateTimeOriginal|Artist|LicenseShortName|ObjectName",
                        "cllimit": "max", "clshow": "!hidden"})
        for p in d.get("query", {}).get("pages", []):
            ii = (p.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata") or {}
            if ii.get("thumburl") and isinstance(meta, dict):
                filas.insert(0, {"id": p.get("pageid"), "titulo": imagen_wd.rsplit(".", 1)[0], "autor_cuenta": ii.get("user"),
                                 "autor": D._texto_plano(meta.get("Artist", {}).get("value")) or ii.get("user"),
                                 "licencia": D._texto_plano(meta.get("LicenseShortName", {}).get("value")),
                                 "datetaken": D._fecha_exif(meta.get("DateTimeOriginal", {}).get("value")),
                                 "url_m": ii.get("thumburl"), "web": ii.get("descriptionurl"), "categorias": ["landscape"],
                                 "wikidata": True})
    df = pd.DataFrame(filas)
    if df.empty:
        return [], 0, [0] * 12
    df["owner"] = df["autor_cuenta"].fillna(df["autor"])
    df["paisaje"] = df["categorias"].map(lambda c: D.clasificar_paisaje(c)[0])
    meses = pd.to_datetime(df["datetaken"], errors="coerce").dropna().dt.month.value_counts()
    de_wd = df["wikidata"].fillna(False).astype(bool) if "wikidata" in df else pd.Series(False, index=df.index)
    elegidas = pd.concat([df[de_wd], df[df.paisaje]]).drop_duplicates("id")
    elegidas = pd.concat([elegidas.drop_duplicates("owner"), elegidas]).drop_duplicates("id").head(maximo)
    fotos = [{"url": r.url_m, "enlace": r.web, "autor": str(r.autor or r.owner or "")[:80], "licencia": r.licencia or "",
              "titulo": str(r.titulo or "")[:120],
              "fecha": None if pd.isna(r.datetaken) else pd.Timestamp(r.datetaken).strftime("%Y-%m-%d")}
             for r in elegidas.itertuples() if r.url_m and (r.licencia or getattr(r, "wikidata", False) is True)]
    return fotos, int(df.owner.nunique()), [int(meses.get(m, 0)) for m in range(1, 13)]


# ---------------------------------------------------------------- main ----
def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--salida", default="public/datos")
    a.add_argument("--total", type=int, default=1500)
    a.add_argument("--por-provincia", type=int, default=12)
    a.add_argument("--minutos", type=float, default=300, help="corta las peticiones a Commons pasado este tiempo")
    a.add_argument("--bbox", help="solo esta caja min_lon,min_lat,max_lon,max_lat (pruebas)")
    args = a.parse_args()
    caja = tuple(float(v) for v in args.bbox.split(",")) if args.bbox else None
    if caja:
        BLOQUES[:] = [caja]
    t0 = time.time()
    salida = Path(args.salida)

    print("[1/5] Candidatos de Wikidata y OpenStreetMap…", flush=True)
    wd, osm = candidatos_wikidata(), candidatos_osm()
    if caja and not wd.empty:
        wd = wd[(wd.lon >= caja[0]) & (wd.lon <= caja[2]) & (wd.lat >= caja[1]) & (wd.lat <= caja[3])]
    cand = fusionar(wd, osm)
    prov = Provincias()
    info = [prov.de(r.lat, r.lon) for r in cand.itertuples()]
    cand["provincia"] = [i["provincia"] if i else None for i in info]
    cand["ccaa"] = [i["ccaa"] if i else None for i in info]
    cand = cand[cand.provincia.notna() & cand.nombre.notna()].reset_index(drop=True)
    print(f"      {len(cand)} candidatos en España", flush=True)

    print("[2/5] Popularidad: fotos de Commons a menos de 500 m…", flush=True)
    n_fotos, cortado = [], False
    for k, r in enumerate(cand.itertuples(), 1):
        if time.time() - t0 > args.minutos * 60:
            cortado = True
            n_fotos.append(None)
            continue
        try:
            n_fotos.append(len(fotos_cerca(r.lat, r.lon)))
        except (RuntimeError, requests.RequestException):
            n_fotos.append(None)
        if k % 500 == 0:
            print(f"      {k}/{len(cand)}", flush=True)
    cand["fotos_cerca"] = n_fotos
    if cortado:
        print("      Tiempo agotado: los candidatos sin contar usan solo Wikidata; la próxima ejecución sigue.")
    cand["puntuacion"] = (np.log1p(cand.fotos_cerca.fillna(0)) + 0.6 * np.log1p(cand.sitelinks.fillna(0))
                          + cand.tipo.map(PESO_TIPO).fillna(0.3) + 0.3 * cand.imagen.notna())

    print("[3/5] Selección por provincia y nacional…", flush=True)
    cand = cand.sort_values("puntuacion", ascending=False)
    fijos = cand.groupby("provincia").head(args.por_provincia)
    resto = cand.drop(fijos.index).head(max(0, args.total - len(fijos)))
    sel = pd.concat([fijos, resto]).sort_values("puntuacion", ascending=False).reset_index(drop=True)
    print(f"      {len(sel)} spots ({sel.provincia.nunique()} provincias)", flush=True)

    print("[4/5] Galerías, horizonte del terreno y contaminación lumínica…", flush=True)
    features = []
    for k, r in enumerate(sel.itertuples(), 1):
        try:
            fotos, autores, meses = galeria(fotos_cerca(r.lat, r.lon), r.imagen if isinstance(r.imagen, str) else None)
        except (RuntimeError, requests.RequestException):
            fotos, autores, meses = [], 0, [0] * 12
        try:
            hz = horizonte.perfil(r.lat, r.lon)
        except requests.RequestException:
            hz = None
        try:
            lp = contaminacion(r.lat, r.lon)
        except requests.RequestException:
            lp = None
        nombre = D.limpiar_nombre(r.nombre) if r.fuente == "osm" else r.nombre
        props = {
            "id": id_spot(nombre, r.lat, r.lon), "nombre": nombre, "tipo_osm": r.tipo, "origen": r.fuente,
            "provincia": r.provincia, "ccaa": r.ccaa, "wikidata": r.wikidata if isinstance(r.wikidata, str) else None,
            "fotos": int(r.fotos_cerca or 0), "fotografos": autores, "fotos_calidad": 0,
            "puntuacion": round(float(r.puntuacion), 2), "sitelinks": int(r.sitelinks or 0),
            "mejor_momento": "desconocido", "pct_amanecer": 0, "pct_atardecer": 0, "pct_noche": 0,
            "meses": meses, "meses_top": [i + 1 for i in np.argsort(meses)[::-1][:3] if meses[i] > 0],
            "galeria": fotos,
            "direccion_vista": r.direccion_vista if isinstance(getattr(r, "direccion_vista", None), str) else None,
            "horizonte": hz, "contaminacion": lp,
        }
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(r.lon, 5), round(r.lat, 5)]},
                         "properties": props})
        if k % 100 == 0:
            print(f"      {k}/{len(sel)}", flush=True)

    print("[5/5] Guardando…", flush=True)
    escribir_json(salida / "spots.geojson", {"type": "FeatureCollection", "zona": "España", "features": features})
    pd.DataFrame([f["properties"] | {"lat": f["geometry"]["coordinates"][1], "lon": f["geometry"]["coordinates"][0]}
                  for f in features]).drop(columns=["galeria", "meses", "horizonte", "contaminacion"]).to_csv(
        salida / "spots.csv", index=False)
    print(f"\n{len(features)} spots → {salida}/spots.geojson ({(salida / 'spots.geojson').stat().st_size / 1e6:.1f} MB)")
    print(sel.groupby("ccaa").size().sort_values(ascending=False).to_string())


if __name__ == "__main__":
    main()
