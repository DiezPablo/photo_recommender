"""Genera eventos.json: calendario del cielo (próximos meses) y eventos de naturaleza.

Uso:
  python -m rasante eventos                                  # → public/datos/eventos.json
  python -m rasante eventos --meses 14 --salida salida/eventos.json
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

from rasante.comun.ficheros import escribir_json
from rasante.eventos import aurora, cielo, naturaleza, starlight


def generar(hoy: date, meses: int, con_red: bool = True) -> dict:
    hasta = hoy + timedelta(days=round(meses * 30.5))
    return {
        "generado": datetime.now(cielo.TZ).isoformat(timespec="minutes"),
        "desde": hoy.isoformat(),
        "hasta": hasta.isoformat(),
        "luna": cielo.fases_luna(hoy, hasta),
        "meteoros": cielo.lluvias_meteoros(hoy, hasta),
        "eclipses": cielo.eclipses(hoy),
        "via_lactea": cielo.via_lactea(hoy, hasta),
        "aurora": aurora.aurora() if con_red else None,
        "starlight": {"zonas": starlight.cargar(), "fuente": starlight.FUENTE},
        "naturaleza": naturaleza.cargar(),
        "categorias": naturaleza.CATEGORIAS,
    }


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="rasante eventos", description=__doc__.splitlines()[0])
    ap.add_argument("--salida", type=Path, default=Path("public/datos/eventos.json"))
    ap.add_argument("--meses", type=int, default=13, help="meses hacia delante del calendario del cielo")
    ap.add_argument("--hoy", type=date.fromisoformat, default=None, help="fecha de inicio (pruebas)")
    a = ap.parse_args(argv)
    datos = generar(a.hoy or datetime.now(cielo.TZ).date(), a.meses)
    escribir_json(a.salida, datos)
    print(
        f"{a.salida}: {len(datos['naturaleza'])} eventos de naturaleza, {len(datos['meteoros'])} lluvias de "
        f"meteoros, {len(datos['eclipses'])} eclipses, {len(datos['via_lactea']['ventanas'])} ventanas de Vía Láctea"
    )
