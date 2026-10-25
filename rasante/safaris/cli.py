"""Safaris en todo el mundo → safaris.json (mensual) y safaris_recientes.json (avistamientos de los últimos 30 días).

Uso:
  python -m rasante safaris --salida public/datos/safaris.json
  python -m rasante safaris --recientes --salida public/datos/safaris_recientes.json
"""

from __future__ import annotations

import argparse
import time
from datetime import date, timedelta
from pathlib import Path

import requests

from rasante.comun.ficheros import escribir_json
from rasante.safaris import entorno, inat
from rasante.safaris.catalogo import cargar

DIAS_RECIENTES = 30
MIN_OBS_ESPECIE = 3  # con una o dos observaciones puede ser un animal de paso o un error: no cuenta como «se ve aquí»
GRUPOS = (("Mammalia", 30), ("Aves", 12), ("Reptilia", 6))
_ERRORES = (requests.RequestException, KeyError, ValueError)


def meses_relativos(grupo: list[int]) -> list[int] | None:
    """Observaciones de mamíferos por mes, de 0 a 100. No se divide entre todas las observaciones: en las zonas
    templadas el invierno saldría «mejor» solo porque no hay flores ni insectos que fotografiar."""
    if sum(grupo) < 50:  # con tan pocas observaciones la forma del año es ruido
        return None
    tope = max(grupo)
    return [round(100 * g / tope) for g in grupo]


def taxones_estrella(parques: list[dict]) -> dict[str, dict]:
    nombres = sorted({c for p in parques for c in p["estrella"]})
    salida = {}
    for c in nombres:
        try:
            t = inat.taxon(c)
        except _ERRORES as e:
            print(f"  sin taxón para {c}: {e}", flush=True)
            continue
        if t is None:
            print(f"  iNaturalist no conoce {c}", flush=True)
            continue
        salida[c] = t
    return salida


def calcular(parques: list[dict], con_clima: bool = True, con_alojamientos: bool = True) -> dict:
    estrella = taxones_estrella(parques)
    ids = [t["taxon"] for t in estrella.values()]
    try:
        wd = entorno.wikidata([p["wikidata"] for p in parques if p["wikidata"]])
    except _ERRORES as e:
        print(f"  sin Wikidata: {e}", flush=True)
        wd = {}
    try:
        fotos = entorno.fotos_commons([w["img"] for w in wd.values() if w.get("img")])
    except (*_ERRORES, RuntimeError) as e:
        print(f"  sin fotos de Commons: {e}", flush=True)
        fotos = {}
    for w in wd.values():
        w["foto"] = fotos.get(w.pop("img", None))
    salida, por_especie = [], {t["taxon"]: [] for t in estrella.values()}
    for i, p in enumerate(parques):
        x = {**p, **{k: v for k, v in (wd.get(p["wikidata"]) or {}).items()}}
        x["estrella"] = [estrella[c]["taxon"] for c in p["estrella"] if c in estrella]
        try:
            x["especies"] = {g: inat.especies(p, g, n) for g, n in GRUPOS}
            cuenta = inat.conteos(p, ids)
            x["conteo_estrella"] = {str(k): v for k, v in cuenta.items()}
            for k, v in cuenta.items():
                por_especie[k].append({"id": p["id"], "n": v})
            x["meses_mamiferos"] = meses_relativos(inat.por_mes(p, "Mammalia"))
            x["observaciones"] = sum(inat.por_mes(p))
        except _ERRORES as e:
            print(f"  {p['nombre']}: sin iNaturalist ({e})", flush=True)
        try:
            if con_clima:
                x["clima"] = entorno.clima(p["lat"], p["lon"])
        except _ERRORES as e:
            print(f"  {p['nombre']}: sin clima ({e})", flush=True)
        try:
            if con_alojamientos:
                x["alojamientos"] = entorno.alojamientos(p["lat"], p["lon"], p["radio_km"])
        except _ERRORES as e:
            print(f"  {p['nombre']}: sin alojamientos ({e})", flush=True)
        salida.append(x)
        print(f"  {i + 1}/{len(parques)} {p['nombre']}", flush=True)
    especies = []
    for c, t in estrella.items():
        lugares = sorted(por_especie[t["taxon"]], key=lambda x: -x["n"])
        especies.append({**t, "cientifico": c, "parques": [x for x in lugares if x["n"] >= MIN_OBS_ESPECIE]})
    especies.sort(key=lambda e: -sum(x["n"] for x in e["parques"]))
    return {"parques": salida, "especies": especies}


def recientes(parques: list[dict], hoy: date | None = None) -> dict:
    """Lo que se ha visto en cada parque en los últimos 30 días: cambia con la temporada y la migración."""
    hoy = hoy or date.today()
    desde = (hoy - timedelta(days=DIAS_RECIENTES)).isoformat()
    estrella = taxones_estrella(parques)
    salida = {}
    for p in parques:
        ids = [estrella[c]["taxon"] for c in p["estrella"] if c in estrella]
        try:
            cuenta = inat.conteos(p, ids, desde, cache=inat.CACHE_RECIENTE)
            mam = inat.especies(p, "Mammalia", 12, desde, cache=inat.CACHE_RECIENTE)
        except _ERRORES as e:
            print(f"  {p['nombre']}: sin iNaturalist ({e})", flush=True)
            continue
        salida[p["id"]] = {
            "estrella": {str(k): v for k, v in cuenta.items()},
            "mamiferos": [{k: m[k] for k in ("taxon", "cientifico", "nombre", "n")} for m in mam],
            "observaciones": sum(m["n"] for m in mam),
        }
    return {"fecha": hoy.isoformat(), "desde": desde, "parques": salida}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="rasante safaris", description=__doc__.splitlines()[0])
    ap.add_argument("--salida", type=Path, default=Path("public/datos/safaris.json"))
    ap.add_argument("--recientes", action="store_true", help="solo los avistamientos de los últimos 30 días")
    ap.add_argument("--solo", help="ids de parques separados por comas (pruebas)")
    ap.add_argument("--sin-clima", action="store_true", help="sin climatología (desde el contenedor Open-Meteo limita)")
    ap.add_argument("--sin-alojamientos", action="store_true", help="sin OSM (desde el contenedor Overpass limita)")
    a = ap.parse_args(argv)
    t0 = time.time()
    parques = cargar()
    if a.solo:
        parques = [p for p in parques if p["id"] in a.solo.split(",")]
    if a.recientes:
        datos = recientes(parques)
        escribir_json(a.salida, datos)
        print(f"{a.salida}: {len(datos['parques'])} parques ({time.time() - t0:.0f} s)")
        return
    datos = calcular(parques, con_clima=not a.sin_clima, con_alojamientos=not a.sin_alojamientos)
    escribir_json(
        a.salida,
        {
            "generado": date.today().isoformat(),
            "fuentes": {
                "parques": "Selección propia; foto, web y artículo de Wikidata y Wikipedia",
                "especies": "iNaturalist (observaciones verificables; fotos con licencia Creative Commons)",
                "clima": f"ERA5 vía Open-Meteo ({entorno.ANOS_CLIMA[0]}-{entorno.ANOS_CLIMA[1]})",
                "alojamientos": "OpenStreetMap (ODbL)",
            },
            **datos,
        },
    )
    print(f"{a.salida}: {len(datos['parques'])} parques, {len(datos['especies'])} especies ({time.time() - t0:.0f} s)")
