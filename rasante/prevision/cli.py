#!/usr/bin/env python3
"""
Condiciones y nota diaria (0-10) de cada spot para foto de paisaje y nocturna.

Lee los spots (spots.geojson de `rasante spots` y mis_spots.csv con los tuyos), pide la
previsión a Open-Meteo y calcula sol, luna y Vía Láctea (rasante.cielo.astro). Para cada spot y día:

  - amanecer / atardecer (modelo de camino de la luz, rasante.notas.nota_luz): nubes por capas en el
    spot en el pico de color (15 min antes de salir / después de ponerse el sol, interpolado),
    nubes bajas a 15/40/80/150 km hacia el sol, aerosoles y polvo (CAMS), humedad y lluvia previa.
  - noche (rasante.notas.nota_astro): calidad hora a hora y mejor ventana de 3 h, transparencia
    (vapor de agua, aerosoles), contaminación lumínica local y cúpula de luz hacia el núcleo de la
    Vía Láctea o el sur.
  - niebla (rasante.notas.nota_niebla): niebla de radiación y mar de nubes con el perfil vertical
    (niveles de presión) en el llano.
  - confianza: la misma nota con las nubes de un segundo modelo (ECMWF IFS); si no coinciden, la
    previsión es dudosa aunque la nota sea alta.

Uso:
  python -m rasante prevision                                   # 5 días → public/datos/informe.json
  python -m rasante prevision --dias 3 --spots public/datos/spots.geojson --mis-spots mis_spots.csv

mis_spots.csv (opcional): nombre,lat,lon[,tipo]   (las líneas que empiezan por # se ignoran)
Open-Meteo es gratuito y sin clave para uso no comercial (también su API de calidad del aire, CAMS).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from rasante.comun.ficheros import escribir_json

from .evaluacion import DIAS_POR_DEFECTO, evaluar, mejores
from .spots import cargar_spots


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        prog="python -m rasante prevision", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--spots", default="public/datos/spots.geojson")
    p.add_argument("--mis-spots", default="mis_spots.csv")
    p.add_argument("--dias", type=int, default=DIAS_POR_DEFECTO)
    p.add_argument("--tz", default="Europe/Madrid")
    p.add_argument("--salida", default="public/datos/informe.json")
    p.add_argument("--top", type=int, default=5, help="mejores por día en pantalla")
    a = p.parse_args(argv)

    try:
        spots = cargar_spots(Path(a.spots), Path(a.mis_spots))
    except SystemExit as e:  # aún no hay spots (primera ejecución): no es un fallo del workflow
        print(e)
        return
    print(f"Evaluando {len(spots)} spots para {a.dias} días…")
    informe = evaluar(spots, a.dias, a.tz)
    escribir_json(Path(a.salida), informe)
    for fecha in informe["fechas"]:
        print(f"\n== {fecha} ==")
        for nota, momento, nombre in mejores(informe, fecha, a.top):
            print(f"  {nota:4.1f}  {momento:9}  {nombre}")
    print(f"\nInforme en {a.salida} ({Path(a.salida).stat().st_size / 1024:.0f} KB)")
