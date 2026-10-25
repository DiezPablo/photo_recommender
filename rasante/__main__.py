"""Punto de entrada: python -m rasante <orden> [opciones]."""

from __future__ import annotations

import importlib
import sys

ORDENES = {
    "prevision": ("rasante.prevision.cli", "Previsión y notas de cada spot → informe.json"),
    "spots": ("rasante.spots.cli", "Descubrir spots en toda España → spots.geojson"),
    "rutas": ("rasante.rutas.cli", "Rutas de senderismo → rutas.json"),
    "eventos": ("rasante.eventos.cli", "Calendario del cielo y de naturaleza → eventos.json"),
    "alineaciones": (
        "rasante.eventos.cli_alineaciones",
        "Sol y luna llena por los picos del horizonte → alineaciones.json",
    ),
    "clima": ("rasante.clima.cli", "Climatología fotográfica por mes (ERA5) → clima.json"),
    "fauna": ("rasante.fauna.cli", "Observatorios de fauna (OSM) con especies y meses (GBIF) → fauna.json"),
    "especies": ("rasante.fauna.cli_especies", "Especies emblemáticas: dónde y cuándo se ven (GBIF) → especies.json"),
    "dron": ("rasante.dron.cli", "¿Se puede volar un dron en cada spot? (ENAIRE y espacios protegidos) → dron.json"),
    "safaris": ("rasante.safaris.cli", "Parques de safari del mundo (iNaturalist, clima, OSM) → safaris.json"),
    "logistica": ("rasante.logistica.cli", "Aparcamientos, refugios y fuentes de OSM cerca → logistica.json"),
    "verificar": ("rasante.verificacion.cli", "Lo previsto frente a lo observado (METAR) → verificacion.json"),
    "validar": ("rasante.validacion.cli", "Validación histórica de las notas"),
    "avisos": ("rasante.avisos.telegram", "Resumen diario por Telegram (opcional)"),
}


def ayuda() -> str:
    filas = "\n".join(f"  {o:<10} {texto}" for o, (_, texto) in ORDENES.items())
    return f"Uso: python -m rasante <orden> [opciones]\n\nÓrdenes:\n{filas}\n\nAyuda de cada orden: python -m rasante <orden> --help"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(ayuda())
        return 0
    orden, resto = argv[0], argv[1:]
    if orden not in ORDENES:
        print(f"Orden desconocida: {orden}\n\n{ayuda()}", file=sys.stderr)
        return 2
    importlib.import_module(ORDENES[orden][0]).main(resto)
    return 0


if __name__ == "__main__":
    sys.exit(main())
