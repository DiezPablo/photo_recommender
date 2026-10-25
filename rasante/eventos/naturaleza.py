"""Eventos de naturaleza con lugar y fechas habituales (lista revisada a mano en recursos/)."""

from __future__ import annotations

import csv
from pathlib import Path

from rasante.comun.territorio import RECURSOS, Provincias, ccaa_de

CSV = RECURSOS / "eventos_naturaleza.csv"
CATEGORIAS = {
    "flora": "Floración",
    "otono": "Otoño",
    "fauna": "Fauna",
    "paisaje": "Paisaje",
    "agua": "Agua",
    "nieve": "Nieve",
}


def _mes_dia(texto: str) -> tuple[int, int]:
    mes, dia = (int(x) for x in texto.split("-"))
    if not (1 <= mes <= 12 and 1 <= dia <= 31):
        raise ValueError(f"fecha mal escrita: {texto} (MM-DD)")
    return mes, dia


def cargar(ruta: Path = CSV, provincias: Provincias | None = None) -> list[dict]:
    """Eventos del CSV con provincia y comunidad. Las fechas quedan como MM-DD (se repiten cada año)."""
    provincias = provincias or Provincias()
    eventos = []
    with open(ruta, encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if fila["categoria"] not in CATEGORIAS:
                raise ValueError(f"{fila['id']}: categoría desconocida {fila['categoria']}")
            for campo in ("desde", "hasta", "pico"):
                _mes_dia(fila[campo])
            lat, lon = float(fila["lat"]), float(fila["lon"])
            info = provincias.de(lat, lon) or {}
            eventos.append(
                {
                    "id": fila["id"],
                    "nombre": fila["nombre"],
                    "categoria": fila["categoria"],
                    "desde": fila["desde"],
                    "hasta": fila["hasta"],
                    "pico": fila["pico"],
                    "lugar": fila["lugar"],
                    "provincia": info.get("provincia"),
                    "ccaa": ccaa_de(info.get("provincia"), info.get("ccaa")),
                    "lat": lat,
                    "lon": lon,
                    "radio_km": float(fila["radio_km"]),
                    "descripcion": fila["descripcion"],
                    "consejo": fila["consejo"],
                }
            )
    ids = [e["id"] for e in eventos]
    if len(ids) != len(set(ids)):
        raise ValueError("ids de evento repetidos")
    return eventos
