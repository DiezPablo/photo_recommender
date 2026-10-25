"""Dónde y cuándo se ve cada especie emblemática, a partir de las observaciones de GBIF.

La lista de especies (con un consejo escrito a mano) está en recursos/especies.csv. Por especie:
- Regiones: en tierra, las provincias con más observaciones (faceta GADM, recuento completo); en el mar,
  unas cajas fijas de costa (Estrecho, Alborán, Canarias…), contadas una a una.
- Zonas: en las regiones con más observaciones se toma una página de registros y se agrupan en celdas de
  0,25° (~25 km). El peso de cada celda es su parte de la muestra por el total de su región. Las especies
  sensibles (lince, oso, lobo…) llegan ya con la ubicación generalizada por los conjuntos de datos; aquí
  además solo se publica el centro de la celda redondeado a 0,05°.
- Meses: observaciones de la especie por mes divididas entre las de su clase (aves o mamíferos) ese mes, para
  quitar el sesgo de que se sale más al campo en primavera.

Lo que se publica es «dónde se ha observado más», no un censo: depende de dónde hay observadores.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

import requests

from rasante.comun.territorio import RECURSOS, Provincias, ccaa_de
from rasante.fauna import gbif
from rasante.spots.commons import consultar, texto_plano

CSV = RECURSOS / "especies.csv"
GRUPOS = {"mamifero", "ave", "marino"}
CELDA = 0.25
MAX_REGIONES = 6
MIN_PARTE_REGION = 0.03  # regiones con menos del 3 % de las observaciones no se muestrean
MAX_ZONAS = 8
# Cajas de mar (lat_min, lat_max, lon_min, lon_max): en el mar no hay provincias que contar
MARES = {
    "Estrecho de Gibraltar": (35.75, 36.3, -6.2, -5.0),
    "Golfo de Cádiz": (36.0, 37.3, -7.5, -6.2),
    "Mar de Alborán": (35.8, 37.0, -5.0, -1.6),
    "Murcia y Alicante": (37.0, 38.6, -1.6, 0.6),
    "Valencia y Castellón": (38.6, 40.5, -0.6, 1.0),
    "Cataluña": (40.5, 42.5, 0.5, 3.6),
    "Baleares": (38.5, 40.3, 1.0, 4.6),
    "Cantábrico": (43.2, 44.5, -7.5, -1.5),
    "Galicia": (41.8, 44.0, -10.0, -7.5),
    "Canarias": (27.5, 29.5, -18.5, -13.0),
}
# Formas domésticas que GBIF cuelga de la especie silvestre (más de la mitad de los «lobos» son perros)
DOMESTICAS = {"Canis lupus familiaris", "Felis silvestris catus", "Felis catus"}
_CLASE = {"ave": gbif.CLASES["aves"], "mamifero": gbif.CLASES["mamiferos"], "marino": gbif.CLASES["mamiferos"]}
_FACETA_MES = [("facet", "month"), ("month.facetLimit", 12)]  # sin el límite GBIF da solo 10 meses
_COMUNES = [
    ("year", f"{gbif.DESDE_ANO},{gbif.HASTA_ANO}"),
    ("occurrenceStatus", "PRESENT"),
    ("hasCoordinate", "true"),
    ("hasGeospatialIssue", "false"),
]


def cargar_lista(ruta: Path = CSV) -> list[dict]:
    """Especies del CSV; falla con un error claro si una fila está mal (mejor que publicar datos cruzados)."""
    especies, vistos = [], set()
    with open(ruta, encoding="utf-8") as f:
        for n, fila in enumerate(csv.DictReader(f), start=2):
            if None in fila or any(v is None for v in fila.values()):
                raise ValueError(f"línea {n}: campos de más o de menos (¿una coma sin comillas?)")
            if any(not fila[c] for c in ("id", "nombre", "cientifico", "grupo", "consejo")):
                raise ValueError(f"línea {n}: falta algún campo obligatorio")
            if fila["grupo"] not in GRUPOS:
                raise ValueError(f"{fila['id']}: grupo desconocido {fila['grupo']}")
            if fila["id"] in vistos:
                raise ValueError(f"{fila['id']}: id repetido")
            vistos.add(fila["id"])
            especies.append({**fila, "eventos": [e for e in fila["eventos"].split("|") if e]})
    return especies


def clave_gbif(cientifico: str) -> int:
    d = gbif._get("species/match", {"name": cientifico, "strict": "true"})
    clave = d.get("speciesKey") or d.get("usageKey")
    if not clave or d.get("matchType") == "NONE":
        raise ValueError(f"GBIF no reconoce {cientifico}")
    return int(clave)


def filtro_taxon(clave: int) -> list[tuple[str, int]]:
    """La especie con sus subespecies, salvo las formas domésticas (que se quitan listando las que quedan)."""
    params = [("taxonKey", clave), ("country", "ES"), *_COMUNES, ("limit", 0), ("facet", "acceptedTaxonKey")]
    d = gbif._get("occurrence/search", params)
    claves = [int(c["name"]) for f in d.get("facets", []) for c in f["counts"]]
    quedan = [k for k in claves if k == clave or gbif._get(f"species/{k}", {}).get("canonicalName") not in DOMESTICAS]
    if len(quedan) == len(claves):
        return [("taxonKey", clave)]
    return [("acceptedTaxonKey", k) for k in quedan]


def _caja(caja: tuple[float, float, float, float]) -> list[tuple[str, str]]:
    la0, la1, lo0, lo1 = caja
    return [("decimalLatitude", f"{la0},{la1}"), ("decimalLongitude", f"{lo0},{lo1}")]


def _meses(d: dict) -> list[int]:
    meses = [0] * 12
    for f in d.get("facets", []):
        if f["field"] == "MONTH":
            for m in f["counts"]:
                meses[int(m["name"]) - 1] = m["count"]
    return meses


def esfuerzo(grupo: str) -> list[int]:
    """Observaciones de toda la clase en España por mes: cuánto se sale al campo cada mes."""
    params = [("classKey", _CLASE[grupo]), ("country", "ES"), *_COMUNES, ("limit", 0), *_FACETA_MES]
    return _meses(gbif._get("occurrence/search", params))


def regiones(taxon: list, grupo: str) -> tuple[int, list[int], list[dict]]:
    """Total de observaciones, observaciones por mes y regiones [{filtro, n}] de más a menos."""
    if grupo == "marino":
        salida, total, meses = [], 0, [0] * 12
        for nombre, caja in MARES.items():
            params = [*taxon, *_caja(caja), *_COMUNES, ("limit", 0), *_FACETA_MES]
            d = gbif._get("occurrence/search", params)
            total += d.get("count", 0)
            meses = [a + b for a, b in zip(meses, _meses(d), strict=True)]
            if d.get("count"):
                salida.append({"nombre": nombre, "filtro": _caja(caja), "n": d["count"]})
        return total, meses, sorted(salida, key=lambda r: -r["n"])
    params = [
        *taxon,
        ("country", "ES"),
        *_COMUNES,
        ("limit", 0),
        ("facet", "gadmLevel2Gid"),
        ("gadmLevel2Gid.facetLimit", 60),
        *_FACETA_MES,
    ]
    d = gbif._get("occurrence/search", params)
    provs = next((f["counts"] for f in d.get("facets", []) if f["field"] == "GADM_LEVEL_2_GID"), [])
    salida = [{"nombre": p["name"], "filtro": [("gadmGid", p["name"])], "n": p["count"]} for p in provs]
    return d.get("count", 0), _meses(d), salida


def muestra(taxon: list, filtro: list[tuple[str, str]], limite: int = 300) -> list[tuple[float, float]]:
    params = [*taxon, *filtro, *_COMUNES, ("limit", limite)]
    d = gbif._get("occurrence/search", params)
    return [
        (r["decimalLatitude"], r["decimalLongitude"])
        for r in d.get("results", [])
        if r.get("decimalLatitude") is not None and r.get("decimalLongitude") is not None
    ]


def provincia_cercana(provincias: Provincias, lat: float, lon: float, max_grados: float = 0.5) -> dict | None:
    """Provincia del punto o, si cae en el mar, la de la costa más cercana (anillos de 0,1°)."""
    info = provincias.de(lat, lon)
    if info:
        return info
    paso = 0.1
    while paso <= max_grados + 1e-9:
        candidatos = []
        for k in range(16):
            a = 2 * math.pi * k / 16
            plat, plon = lat + paso * math.sin(a), lon + paso * math.cos(a) / math.cos(math.radians(lat))
            if (p := provincias.de(plat, plon)) is not None:
                candidatos.append(p)
        if candidatos:
            return candidatos[0]
        paso += 0.1
    return None


def zonas(muestras: list[dict], provincias: Provincias, maximo: int = MAX_ZONAS) -> list[dict]:
    """Celdas con más observaciones estimadas a partir de las muestras [{n, puntos}] de cada región."""
    celdas: dict[tuple[int, int], dict] = defaultdict(lambda: {"est": 0.0, "n": 0, "lat": 0.0, "lon": 0.0})
    for m in muestras:
        if not m["puntos"]:
            continue
        por_punto = m["n"] / len(m["puntos"])
        for lat, lon in m["puntos"]:
            c = celdas[(math.floor(lat / CELDA), math.floor(lon / CELDA))]
            c["est"] += por_punto
            c["n"] += 1
            c["lat"] += lat
            c["lon"] += lon
    # una celda con un solo registro de la muestra es ruido, salvo que la especie apenas tenga registros
    minimo = 2 if sum(c["n"] for c in celdas.values()) >= 30 else 1
    salida = []
    for c in sorted(celdas.values(), key=lambda c: -c["est"]):
        if c["n"] < minimo:
            continue
        lat, lon = round(c["lat"] / c["n"] / 0.05) * 0.05, round(c["lon"] / c["n"] / 0.05) * 0.05
        info = provincia_cercana(provincias, lat, lon)
        if info is None:  # en un país vecino o mar adentro
            continue
        salida.append(
            {
                "lat": round(lat, 2),
                "lon": round(lon, 2),
                "provincia": info["provincia"],
                "ccaa": ccaa_de(info["provincia"], info.get("ccaa")),
                "est": c["est"],
            }
        )
        if len(salida) == maximo:
            break
    tope = salida[0]["est"] if salida else 1
    for z in salida:
        z["peso"] = max(1, round(100 * z.pop("est") / tope))
    return salida


def indice_meses(especie: list[int], clase: list[int]) -> list[int]:
    """Observaciones de la especie relativas al esfuerzo de cada mes, de 0 a 100."""
    rel = [e / c if c else 0.0 for e, c in zip(especie, clase, strict=True)]
    tope = max(rel) or 1.0
    return [round(100 * r / tope) for r in rel]


WIKIDATA = "https://query.wikidata.org/sparql"


def fotos(cientificos: list[str]) -> dict[str, dict]:
    """Foto de cada especie (la imagen de su elemento de Wikidata) con autor y licencia de Commons."""
    valores = " ".join(f'"{c}"' for c in cientificos)
    consulta = f"SELECT ?n ?img WHERE {{ VALUES ?n {{ {valores} }} ?t wdt:P225 ?n; wdt:P18 ?img. }}"
    clave = "wikidata:" + consulta
    filas = gbif.CACHE.leer(clave)
    if filas is None:
        r = gbif._SESION.get(WIKIDATA, params={"query": consulta, "format": "json"}, timeout=60)
        r.raise_for_status()
        filas = r.json()["results"]["bindings"]
        gbif.CACHE.guardar(clave, filas)
    fichero = {}
    for f in filas:  # si un taxón tiene varias imágenes, la primera
        fichero.setdefault(f["n"]["value"], "File:" + unquote(f["img"]["value"].rsplit("/", 1)[1]))
    titulos = sorted(set(fichero.values()))
    info: dict[str, dict] = {}
    for i in range(0, len(titulos), 50):
        d = consultar(
            {
                "titles": "|".join(titulos[i : i + 50]),
                "prop": "imageinfo",
                "iiprop": "url|user|extmetadata",
                "iiurlwidth": 640,
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
                "url": ii["thumburl"].split("?")[0],  # sin los parámetros de seguimiento
                "web": ii.get("descriptionurl"),
                "autor": texto_plano(meta.get("Artist", {}).get("value")) or ii.get("user"),
                "licencia": texto_plano(meta.get("LicenseShortName", {}).get("value")),
            }
    return {c: info[t] for c, t in fichero.items() if t in info}


def calcular(lista: list[dict], provincias: Provincias | None = None) -> list[dict]:
    provincias = provincias or Provincias()
    esfuerzos = {g: esfuerzo(g) for g in {e["grupo"] for e in lista}}
    salida = []
    for e in lista:
        try:
            clave = clave_gbif(e["cientifico"])
            taxon = filtro_taxon(clave)
            total, meses, regs = regiones(taxon, e["grupo"])
            elegidas = [r for r in regs[:MAX_REGIONES] if r["n"] >= MIN_PARTE_REGION * total]
            muestras = [{"n": r["n"], "puntos": muestra(taxon, r["filtro"])} for r in elegidas]
        except (requests.RequestException, ValueError) as err:
            print(f"  sin GBIF para {e['nombre']}: {err}", flush=True)
            continue
        zs = zonas(muestras, provincias)
        print(f"  {e['nombre']}: {total} observaciones, {len(zs)} zonas", flush=True)
        salida.append(
            {
                "id": e["id"],
                "nombre": e["nombre"],
                "cientifico": e["cientifico"],
                "grupo": e["grupo"],
                "gbif": clave,
                "observaciones": total,
                "meses": indice_meses(meses, esfuerzos[e["grupo"]]),
                "zonas": zs,
                "eventos": e["eventos"],
                "consejo": e["consejo"],
            }
        )
    try:
        fs = fotos([e["cientifico"] for e in salida])
    except (requests.RequestException, RuntimeError, KeyError) as err:
        print(f"  sin fotos: {err}", flush=True)
        fs = {}
    for e in salida:
        e["foto"] = fs.get(e["cientifico"])
    return salida
