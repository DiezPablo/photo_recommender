"""
Rutas de senderismo de toda España → public/datos/rutas.json

Fuentes (gratuitas y abiertas):
  - OpenStreetMap: relaciones route=hiking/foot de un extracto PBF de España (Geofabrik u openstreetmap.fr).
    Se lee el fichero entero sin consultas a Overpass. ODbL, con atribución.
  - Senderos homologados FEDME (GR, PR, SL) del servicio del IGN. CC BY 4.0 (FEDME). Cuando un sendero
    FEDME coincide con una ruta de OSM, se le pone el nombre oficial y el enlace a misendafedme.es; si no,
    entra como ruta propia.
  - Caminos Naturales (Ministerio de Agricultura, Pesca y Alimentación), mismo tratamiento.

Para cada ruta: trazado (simplificado a ~10 m, en «encoded polyline»), distancia, desnivel y perfil con el
modelo digital del terreno (rasante.terreno.horizonte.altura), tiempo y dificultad estimados con el método MIDE (sin el
medio ni la orientación, que no se conocen), circular o lineal, provincia y comunidad.

Uso:
  python -m rasante rutas --pbf spain-latest.osm.pbf                 # → public/datos/rutas.json
  python -m rasante rutas --pbf madrid.osm.pbf --sin-ign --salida /tmp
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from rasante.comun.ficheros import escribir_json
from rasante.comun.territorio import Provincias
from rasante.terreno import horizonte

from .calculo import completar
from .fusion import fusionar, nombrar, quitar_duplicados
from .ign import leer_ign
from .osm import leer_osm


def main(argv: list[str] | None = None) -> None:
    a = argparse.ArgumentParser(
        prog="python -m rasante rutas", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    a.add_argument("--pbf", required=True, help="extracto de OpenStreetMap de España (.osm.pbf)")
    a.add_argument("--salida", default="public/datos")
    a.add_argument("--sin-ign", action="store_true", help="solo OSM (pruebas sin red)")
    args = a.parse_args(argv)

    print("[1/4] OpenStreetMap…", flush=True)
    rutas = leer_osm(Path(args.pbf))
    print(f"      {len(rutas)} rutas con nombre", flush=True)
    if not args.sin_ign:
        print("[2/4] Senderos homologados FEDME y Caminos Naturales (IGN)…", flush=True)
        rutas = fusionar(rutas, leer_ign())
    print("[3/4] Recorrido, desnivel y tiempo…", flush=True)
    prov = Provincias()
    t0 = time.time()
    # en orden geográfico, para reutilizar las teselas del DEM y poder vaciar la caché en memoria
    rutas.sort(key=lambda r: (round(r["tramos"][0][0][1], 0), r["tramos"][0][0][0]) if r["tramos"] else (0, 0))
    salida = []
    for k, r in enumerate(rutas, 1):
        if not r["tramos"]:
            continue
        c = completar(r, prov)
        if c:
            salida.append(c)
        if len(horizonte._teselas) > 1500:
            horizonte._teselas.clear()
        if k % 500 == 0:
            print(f"      {k}/{len(rutas)} ({(time.time() - t0) / 60:.0f} min)", flush=True)
    vistos, unicas = set(), []
    for r in salida:
        if r["id"] not in vistos:
            vistos.add(r["id"])
            unicas.append(r)
    unicas = quitar_duplicados(unicas)
    nombrar(unicas)
    print("[4/4] Guardando…", flush=True)
    destino = Path(args.salida) / "rutas.json"
    escribir_json(
        destino,
        {
            "generado": time.strftime("%Y-%m-%dT%H:%M%z"),
            "fuentes": {
                "osm": "© colaboradores de OpenStreetMap (ODbL)",
                "fedme": "Senderos FEDME (CC BY 4.0)",
                "mapa": "Caminos Naturales © Ministerio de Agricultura, Pesca y Alimentación",
                "dem": "Teselas de elevación Terrarium (Mapzen/AWS Open Data)",
            },
            "rutas": unicas,
        },
    )
    print(f"\n{len(unicas)} rutas → {destino} ({destino.stat().st_size / 1e6:.1f} MB)")
