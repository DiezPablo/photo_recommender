"""Climatología fotográfica por mes (ERA5 2021-2025) → clima.json.

Descarga los puntos de la rejilla que falten sin pasar del presupuesto de llamadas de Open-Meteo y, cuando
están todos, calcula las probabilidades por mes. Pensado para ejecutarse varias veces (Actions, con la
caché de cache/clima) hasta completar la rejilla; después solo recalcula.

Uso:
  python -m rasante clima --presupuesto 4000            # descarga lo que quepa; si está completa, agrega
  python -m rasante clima --solo-agregar --salida salida/clima.json
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path

import requests

from rasante.clima import agregar, era5, rejilla
from rasante.comun.ficheros import escribir_json


def descargar_pendientes(presupuesto: float, dir: Path) -> tuple[int, int]:
    puntos = rejilla.puntos()
    pendientes = [p for p in puntos if not era5.fichero(*p, dir=dir).exists()]
    gastado = 0.0
    hechos = 0
    inicio = time.monotonic()
    for i, (lat, lon) in enumerate(pendientes):
        coste = era5.coste()
        if gastado + coste > presupuesto:
            break
        # ritmo: un punto cada PAUSA_S como mínimo (< 5000 llamadas a la hora), contando lo que tardó la descarga
        if i:
            time.sleep(max(0.0, era5.PAUSA_S - (time.monotonic() - inicio)))
        inicio = time.monotonic()
        try:
            df = era5.descargar(lat, lon)
        except (requests.RequestException, RuntimeError) as e:
            # un punto que no sale no para la ejecución: se intentará en la siguiente
            print(
                f"  {lat:.2f}, {lon:.2f}: no se pudo descargar ({e.__class__.__name__}); queda para otra vez",
                flush=True,
            )
            gastado += coste
            continue
        era5.guardar(era5.resumir(df, lat, lon), era5.fichero(lat, lon, dir=dir))
        gastado += coste
        hechos += 1
        print(
            f"  {lat:.2f}, {lon:.2f}: {len(puntos) - len(pendientes) + hechos}/{len(puntos)} ({gastado:.0f} llamadas)",
            flush=True,
        )
    return len(puntos) - len(pendientes) + hechos, len(puntos)


def agregar_todo(dir: Path) -> dict:
    resumenes = {}
    for p in rejilla.puntos():
        f = era5.fichero(*p, dir=dir)
        if f.exists():
            resumenes[p] = era5.leer(f)
    datos = agregar.cargar_datos(resumenes)
    puntos = []
    for i, (lat, lon) in enumerate(resumenes):
        m = agregar.por_mes(agregar.notas_punto(datos, lat, lon))
        puntos.append({"lat": lat, "lon": lon, **m})
        if i % 50 == 0:
            print(f"  agregado {i}/{len(resumenes)}", flush=True)
    return {
        "generado": datetime.now(era5.TZ).isoformat(timespec="minutes"),
        "desde": era5.DESDE.isoformat(),
        "hasta": era5.HASTA.isoformat(),
        "paso": rejilla.PASO,
        "nota_buena": agregar.NOTA_BUENA,
        "horas_noche": agregar.HORAS_NOCHE,
        "puntos": puntos,
    }


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="rasante clima", description=__doc__.splitlines()[0])
    ap.add_argument("--presupuesto", type=float, default=4000, help="llamadas de Open-Meteo como máximo")
    ap.add_argument("--dir", type=Path, default=era5.DIR, help="resúmenes por punto (caché)")
    ap.add_argument("--salida", type=Path, default=Path("public/datos/clima.json"))
    ap.add_argument("--solo-agregar", action="store_true", help="no descargar; agregar lo que haya")
    a = ap.parse_args(argv)
    hechos, total = (0, 0) if a.solo_agregar else descargar_pendientes(a.presupuesto, a.dir)
    if not a.solo_agregar and hechos < total:
        print(f"Rejilla incompleta ({hechos}/{total}): se agregará cuando esté entera.")
        return
    datos = agregar_todo(a.dir)
    escribir_json(a.salida, datos)
    print(f"{a.salida}: {len(datos['puntos'])} puntos")
