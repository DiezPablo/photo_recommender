"""Todos los parques del mundo con fauna → safaris_mundo.json (fichas) y safaris_indice.json (buscador).

Uso:
  python -m rasante safaris --mundo [--osm-max 1500] [--hilos 4]
"""

from __future__ import annotations

import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import requests

from rasante.comun.ficheros import escribir_json
from rasante.fauna import gbif as gbif_nombres
from rasante.safaris import entorno, mundo, practico
from rasante.safaris.catalogo import cargar

_ERRORES = (requests.RequestException, KeyError, ValueError, RuntimeError)
EXTERIORES = "https://www.exteriores.gob.es/"


def _en_paralelo(funcion, elementos, hilos: int, etiqueta: str):
    salida = [None] * len(elementos)
    t0 = time.time()

    def uno(i):
        try:
            salida[i] = funcion(elementos[i])
        except _ERRORES as e:
            print(f"    {etiqueta}: fallo en {i}: {e}", flush=True)

    with ThreadPoolExecutor(hilos) as ex:
        for n, _ in enumerate(ex.map(uno, range(len(elementos)))):
            if n and n % 500 == 0:
                print(f"  {etiqueta}: {n}/{len(elementos)} ({time.time() - t0:.0f} s)", flush=True)
    return salida


def nombre(clave: int) -> dict | None:
    """Nombre común en español de GBIF; sin tiempo, solo si ya está en la caché."""
    if mundo.sin_tiempo():
        en_cache = [
            gbif_nombres.CACHE.leer(json.dumps({"ruta": r, "params": p}))
            for r, p in ((f"species/{clave}", {}), (f"species/{clave}/vernacularNames", {"limit": 500}))
        ]
        if any(x is None for x in en_cache):
            return None
    return gbif_nombres.nombre_comun(clave)


def puntuacion(n_especies: int, obs: int, n_estrella: int = 0) -> float:
    """Más peso a las especies emblemáticas (lo que se va a ver en un safari) que a la riqueza total, que en
    los trópicos se llena de murciélagos y roedores."""
    return round(25 * n_estrella + min(n_especies, 80) * math.log10(obs + 10) / 2, 1)


def claves_estrella(curados: list[dict]) -> dict[int, str]:
    """Clave de GBIF de las especies estrella del catálogo curado (para filtrar parques por especie)."""
    salida = {}
    for c in sorted({c for p in curados for c in p["estrella"]}):
        try:
            d = gbif_nombres._get("species/match", {"name": c, "strict": "true"})
        except _ERRORES:
            continue
        clave = d.get("speciesKey") or d.get("usageKey")
        if clave and d.get("matchType") != "NONE":
            salida[int(clave)] = c
    return salida


def quitar_duplicados(parques: list[dict]) -> list[dict]:
    """El mismo parque con dos elementos de Wikidata (p. ej. parque nacional y reserva de la biosfera)."""
    parques = sorted(parques, key=lambda p: -p["puntuacion"])
    vistos: list[dict] = []
    for p in parques:
        nombre = mundo.slug(p["nombre"])
        if any(
            mundo.slug(v["nombre"]) == nombre and practico.km((p["lat"], p["lon"]), (v["lat"], v["lon"])) < 40
            for v in vistos
        ):
            continue
        vistos.append(p)
    return vistos


def calcular(hilos: int = 4, osm_max: int = 1500, limite: int | None = None) -> dict:
    curados = cargar()
    estrella = claves_estrella(curados)
    cands = mundo.candidatos()
    qids_curados = {c["wikidata"]: c for c in curados if c["wikidata"]}
    lista = [
        {"qid": q, **x, "radio_km": mundo.radio_km(x["area_m2"], x["clase"])}
        for q, x in cands.items()
        if q not in qids_curados
    ][:limite]
    # los parques del catálogo curado entran siempre, con su zona de safari
    lista += [
        {
            "qid": c["wikidata"],
            "id": c["id"],
            "lat": c["lat"],
            "lon": c["lon"],
            "radio_km": c["radio_km"],
            "area_m2": (cands.get(c["wikidata"]) or {}).get("area_m2"),
            "pais": (cands.get(c["wikidata"]) or {}).get("pais"),
            "clase": (cands.get(c["wikidata"]) or {}).get("clase", "parque nacional"),
            "destacado": True,
        }
        for c in curados
    ]
    print(f"  {len(lista)} candidatos; cribado con GBIF…", flush=True)
    mam = _en_paralelo(lambda x: mundo.gbif(x["lat"], x["lon"], x["radio_km"], mundo.MAMIFEROS), lista, hilos, "GBIF")
    elegidos = []
    for x, g in zip(lista, mam, strict=True):
        if g is None:
            continue
        # el «lobo» sin los perros
        for especie, domestica in mundo.SUBESPECIE_DOMESTICA.items():
            fila = next((e for e in g["especies"] if e[0] == especie), None)
            if fila:
                try:
                    perros = mundo.conteo_taxon(x["lat"], x["lon"], x["radio_km"], domestica)
                except _ERRORES:
                    perros = 0
                g = {
                    **g,
                    "especies": [e if e[0] != especie else [especie, max(0, e[1] - perros)] for e in g["especies"]],
                }
                g["especies"] = sorted([e for e in g["especies"] if e[1] > 0], key=lambda e: -e[1])
        if x.get("destacado") or (len(g["especies"]) >= mundo.MIN_ESPECIES and g["obs"] >= mundo.MIN_OBS):
            elegidos.append({**x, "mam": g})
    print(f"  {len(elegidos)} parques con fauna", flush=True)

    det = mundo.detalles([x["qid"] for x in elegidos if x["qid"]])
    paises = mundo.paises([x["pais"] for x in elegidos if x["pais"]])
    parques = []
    for x in elegidos:
        d = det.get(x["qid"] or "", {})
        nombre = next((c["nombre"] for c in curados if c["id"] == x.get("id")), None) or d.get("es") or d.get("en")
        if not nombre or nombre == x["qid"]:
            continue
        g = x["mam"]
        parques.append(
            {
                "id": x.get("id") or f"{mundo.slug(nombre) or 'parque'}-{x['qid'].lower()}",
                "qid": x["qid"],
                "nombre": nombre,
                "clase": x["clase"],
                "pais": x["pais"],
                "lat": round(x["lat"], 4),
                "lon": round(x["lon"], 4),
                "radio_km": x["radio_km"],
                "area_km2": round(x["area_m2"] / 1e6) if x.get("area_m2") else None,
                "iucn": d.get("iucnl"),
                "unesco": bool(d.get("unesco")),
                "wdpa": d.get("wdpa"),
                "web": d.get("web"),
                "wiki": d.get("wiki"),
                "img": d.get("img"),
                "destacado": bool(x.get("destacado")),
                "temporada": next((c["meses"] for c in curados if c["id"] == x.get("id")), None),
                # país del catálogo, por si el elemento de Wikidata no lo tiene (el Masái Mara es una región)
                **next(
                    (
                        {"pais_nombre": c["pais"], "continente": c["continente"]}
                        for c in curados
                        if c["id"] == x.get("id")
                    ),
                    {},
                ),
                "obs": g["obs"],
                "n_mamiferos": len(g["especies"]),
                "mamiferos": g["especies"][:15],
                "estrella": {str(k): n for k, n in g["especies"] if k in estrella},
                "meses": g["meses"],
                "puntuacion": puntuacion(
                    len(g["especies"]), g["obs"], sum(1 for k, n in g["especies"] if k in estrella and n >= 5)
                ),
            }
        )
    parques = quitar_duplicados(parques)
    print(f"  {len(parques)} parques tras quitar duplicados; aves, clima y cómo llegar…", flush=True)

    aves = _en_paralelo(lambda p: mundo.gbif(p["lat"], p["lon"], p["radio_km"], mundo.AVES, 40), parques, hilos, "aves")
    climas = _en_paralelo(lambda p: practico.clima(p["lat"], p["lon"]), parques, min(hilos, 3), "clima")
    aeropuertos = practico.Aeropuertos()
    try:
        fotos = entorno.fotos_commons([p["img"] for p in parques if p["img"]])
    except _ERRORES as e:
        print(f"  sin fotos de Commons: {e}", flush=True)
        fotos = {}
    # OSM por tandas: primero los más importantes; el resto, de la caché si ya se pidió otra vez
    orden = sorted(range(len(parques)), key=lambda i: (not parques[i]["destacado"], -parques[i]["puntuacion"]))
    pedir_osm = set(orden[:osm_max])
    osm = _en_paralelo(
        lambda i: practico.osm(parques[i]["lat"], parques[i]["lon"], parques[i]["radio_km"], i not in pedir_osm),
        list(range(len(parques))),
        2,
        "OSM",
    )
    for p, a, c, o in zip(parques, aves, climas, osm, strict=True):
        p["aves"] = (a or {}).get("especies", [])[:10]
        p["lluvia_mm"] = c["lluvia_mm"] if c else None
        p["meses_secos"] = practico.meses_secos(c)
        p["llegar"] = aeropuertos.llegar(p["lat"], p["lon"], p["radio_km"])
        p["foto"] = fotos.get(p.pop("img")) if p.get("img") else p.pop("img", None)
        if o is not None:
            p["osm"] = o
    con_osm = sum(1 for p in parques if "osm" in p)
    print(f"  OSM: {con_osm}/{len(parques)} parques", flush=True)

    claves = {k for p in parques for k, _ in (p["mamiferos"] + p["aves"])} | set(estrella)
    nombres_lista = sorted(claves)
    print(f"  nombres de {len(nombres_lista)} especies…", flush=True)
    nombres = _en_paralelo(nombre, nombres_lista, hilos, "nombres")
    especies = {
        str(k): {"c": n["cientifico"], "n": n["nombre"]} for k, n in zip(nombres_lista, nombres, strict=True) if n
    }
    # fuera los animales domésticos de las listas
    domesticos = {int(k) for k, e in especies.items() if e["c"] in mundo.DOMESTICOS}
    for p in parques:
        p["mamiferos"] = [e for e in p["mamiferos"] if e[0] not in domesticos][:12]
        p["aves"] = [e for e in p["aves"] if e[0] not in domesticos]
    return {
        "paises": {
            q: {
                "nombre": d.get("n"),
                "continente": mundo.CONTINENTE.get(d.get("cont", ""), d.get("cont")),
                "moneda": d.get("mon"),
                "idiomas": d["idiomas"][:3],
            }
            for q, d in paises.items()
        },
        "especies": especies,
        "estrella": {str(k): c for k, c in estrella.items()},
        "parques": parques,
    }


def indice(datos: dict) -> list[dict]:
    """Lo justo para el buscador del navegador."""
    salida = []
    for p in datos["parques"]:
        pais = datos["paises"].get(p["pais"] or "", {})
        salida.append(
            {
                "id": p["id"],
                "n": p["nombre"],
                "p": pais.get("nombre") or p.get("pais_nombre"),
                "c": pais.get("continente") or p.get("continente"),
                "la": p["lat"],
                "lo": p["lon"],
                "r": p["radio_km"],
                "s": p["puntuacion"],
                "m": p["n_mamiferos"],
                "e": [int(k) for k in p["estrella"]],
                "sec": p["meses_secos"],
                "d": p["destacado"],
                **({"t": p["temporada"]} if p.get("temporada") else {}),
                "f": (p.get("foto") or {}).get("url"),
            }
        )
    return sorted(salida, key=lambda x: -x["s"])


def main(
    salida: Path, indice_salida: Path, hilos: int, osm_max: int, limite: int | None = None, minutos: float | None = None
) -> None:
    t0 = time.time()
    if minutos:
        mundo.LIMITE[0] = t0 + minutos * 60
    datos = calcular(hilos, osm_max, limite)
    escribir_json(
        salida,
        {
            "generado": date.today().isoformat(),
            "fuentes": {
                "parques": "Wikidata (CC0)",
                "fauna": f"GBIF.org, mamíferos y aves desde {mundo.DESDE_ANO}",
                "lluvia": "NASA POWER (climatología 2001-2025)",
                "aeropuertos": "OurAirports (dominio público)",
                "servicios": "OpenStreetMap (ODbL)",
                "viajar": EXTERIORES,
            },
            **datos,
        },
    )
    escribir_json(indice_salida, {"generado": date.today().isoformat(), "parques": indice(datos)})
    print(f"{salida}: {len(datos['parques'])} parques ({time.time() - t0:.0f} s)")
