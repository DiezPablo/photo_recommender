"""
Spots de fotografía de paisaje en toda España.

Candidatos (sin clave de API):
  - Wikidata: lugares con foto (P18) y coordenadas en España de tipos fotogénicos (montañas, lagos,
    embalses, playas, cascadas, miradores, cabos, faros, cañones, acantilados). Los "sitelinks"
    (artículos en Wikipedia) miden lo conocido que es.
  - OpenStreetMap (Overpass, por bloques): miradores con nombre, cumbres con Wikidata, cascadas,
    faros, cabos y acantilados con nombre.
Popularidad: número de fotos geolocalizadas en Wikimedia Commons a menos de 500 m.
Selección: los mejores de cada provincia (para cubrir todo el país) y el resto por puntuación nacional.
Para cada spot elegido: galería de Commons (autor y licencia), horizonte del terreno (rasante.terreno.horizonte),
contaminación lumínica (rasante.cielo.contaminacion), provincia y comunidad autónoma.

El primer cálculo hace ~13 000 peticiones a Commons (≈ 2 h en GitHub Actions); todo queda en
cache/ y las ejecuciones siguientes solo piden lo nuevo. Con --minutos se corta a tiempo y la
siguiente ejecución continúa.

Uso:
  python -m rasante spots --salida public/datos             # ~1500 spots
  python -m rasante spots --total 300 --por-provincia 4     # prueba rápida
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from rasante.cielo.contaminacion import contaminacion
from rasante.comun.ficheros import escribir_json
from rasante.comun.ids import id_spot
from rasante.comun.territorio import Provincias, ccaa_de
from rasante.terreno import horizonte

from . import candidatos
from .candidatos import candidatos_osm, candidatos_wikidata, fusionar
from .commons import fotos_cerca, galeria
from .nombres import limpiar_nombre, nombre_valido
from .seleccion import PESO_TIPO, ajuste_cielo, entero


def main(argv: list[str] | None = None) -> None:
    a = argparse.ArgumentParser(
        prog="python -m rasante spots", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    a.add_argument("--salida", default="public/datos")
    a.add_argument("--total", type=int, default=1500)
    a.add_argument("--por-provincia", type=int, default=12)
    a.add_argument("--minutos", type=float, default=300, help="corta las peticiones a Commons pasado este tiempo")
    a.add_argument("--bbox", help="solo esta caja min_lon,min_lat,max_lon,max_lat (pruebas)")
    args = a.parse_args(argv)
    caja = tuple(float(v) for v in args.bbox.split(",")) if args.bbox else None
    if caja:
        candidatos.BLOQUES[:] = [caja]
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
    cand["ccaa"] = [ccaa_de(i["provincia"], i["ccaa"]) if i else None for i in info]
    cand = cand[cand.provincia.notna() & cand.nombre.notna()]
    cand = cand[
        [nombre_valido(limpiar_nombre(n) if f == "osm" else n) for n, f in zip(cand.nombre, cand.fuente, strict=True)]
    ]
    cand = cand.reset_index(drop=True)
    print(f"      {len(cand)} candidatos en España", flush=True)

    print("[2/5] Popularidad: fotos de Commons a menos de 500 m…", flush=True)
    t0 = time.time()  # el presupuesto de --minutos es solo para Commons
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
            print(f"      {k}/{len(cand)} ({(time.time() - t0) / 60:.0f} min)", flush=True)
    cand["fotos_cerca"] = pd.to_numeric(pd.Series(n_fotos, index=cand.index), errors="coerce").astype(float)
    cand["sitelinks"] = pd.to_numeric(cand["sitelinks"], errors="coerce").fillna(0).astype(float)
    if cortado:
        print("      Tiempo agotado: los candidatos sin contar usan solo Wikidata; la próxima ejecución sigue.")
    cand["cielo"] = [ajuste_cielo(la, lo) for la, lo in zip(cand.lat, cand.lon, strict=True)]
    cand["puntuacion"] = (
        np.log1p(cand.fotos_cerca.fillna(0))
        + 0.6 * np.log1p(cand.sitelinks.fillna(0))
        + cand.tipo.map(PESO_TIPO).fillna(0.3)
        + 0.3 * cand.imagen.notna()
        + cand.cielo
    )

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
        nombre = limpiar_nombre(r.nombre) if r.fuente == "osm" else r.nombre
        props = {
            "id": id_spot(nombre, r.lat, r.lon),
            "nombre": nombre,
            "tipo_osm": r.tipo,
            "origen": r.fuente,
            "provincia": r.provincia,
            "ccaa": r.ccaa,
            "wikidata": r.wikidata if isinstance(r.wikidata, str) else None,
            "fotos": entero(r.fotos_cerca),
            "fotografos": autores,
            "fotos_calidad": 0,
            "puntuacion": round(float(r.puntuacion), 2),
            "sitelinks": entero(r.sitelinks),
            "mejor_momento": "desconocido",
            "pct_amanecer": 0,
            "pct_atardecer": 0,
            "pct_noche": 0,
            "meses": meses,
            "meses_top": [i + 1 for i in np.argsort(meses)[::-1][:3] if meses[i] > 0],
            "galeria": fotos,
            "direccion_vista": r.direccion_vista if isinstance(getattr(r, "direccion_vista", None), str) else None,
            "horizonte": hz,
            "contaminacion": lp,
        }
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(r.lon, 5), round(r.lat, 5)]},
                "properties": props,
            }
        )
        if k % 100 == 0:
            print(f"      {k}/{len(sel)}", flush=True)

    print("[5/5] Guardando…", flush=True)
    escribir_json(salida / "spots.geojson", {"type": "FeatureCollection", "zona": "España", "features": features})
    pd.DataFrame(
        [
            f["properties"] | {"lat": f["geometry"]["coordinates"][1], "lon": f["geometry"]["coordinates"][0]}
            for f in features
        ]
    ).drop(columns=["galeria", "meses", "horizonte", "contaminacion"]).to_csv(salida / "spots.csv", index=False)
    print(
        f"\n{len(features)} spots → {salida}/spots.geojson ({(salida / 'spots.geojson').stat().st_size / 1e6:.1f} MB)"
    )
    print(sel.groupby("ccaa").size().sort_values(ascending=False).to_string())
