"""Especies emblemáticas: dónde y cuándo se ven en España (GBIF) → especies.json.

Uso:
  python -m rasante especies --salida public/datos/especies.json
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from rasante.comun.ficheros import escribir_json
from rasante.fauna import gbif
from rasante.fauna.especies import CSV, calcular, cargar_lista


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="rasante especies", description=__doc__.splitlines()[0])
    ap.add_argument("--lista", type=Path, default=CSV)
    ap.add_argument("--salida", type=Path, default=Path("public/datos/especies.json"))
    a = ap.parse_args(argv)
    t0 = time.time()
    especies = calcular(cargar_lista(a.lista))
    escribir_json(
        a.salida,
        {
            "fuentes": {
                "observaciones": f"GBIF.org, {gbif.DESDE_ANO}-{gbif.HASTA_ANO} (eBird, iNaturalist, Observation.org…)",
                "fotos": "Wikidata y Wikimedia Commons",
            },
            "especies": especies,
        },
    )
    print(f"{a.salida}: {len(especies)} especies ({time.time() - t0:.0f} s)")
