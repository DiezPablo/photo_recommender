"""Rutas de senderismo de OpenStreetMap a partir de un extracto PBF (sin Overpass)."""

from __future__ import annotations

import re
import time
from pathlib import Path

from .geometria import partes_unidas
from .metricas import tipo_ruta

# Roles de miembros que no son el camino principal
ROLES_FUERA = {"alternative", "excursion", "approach", "connection", "link", "guidepost", "platform", "stop"}


# Redes de bici, caballo… que a veces se cuelan con route=foot
RED_FUERA = re.compile(r"^(?:[lrni]cn|[lrni]hn)$")


def leer_osm(pbf: Path) -> list[dict]:
    """Relaciones de senderismo con la geometría de sus vías. Dos pasadas por el fichero: relaciones
    (y sus vías) y vías con las coordenadas de sus nodos."""
    import osmium

    t0 = time.time()
    rels = {}
    for r in osmium.FileProcessor(str(pbf), osmium.osm.RELATION):
        tg = dict(r.tags)
        if tg.get("type") != "route" or tg.get("route") not in ("hiking", "foot"):
            continue
        if RED_FUERA.match(tg.get("network", "")) or tg.get("state") in ("proposed", "disused", "abandoned"):
            continue
        vias = [m.ref for m in r.members if m.type == "w" and m.role not in ROLES_FUERA]
        if not vias:  # superrutas (relaciones de relaciones): sus etapas ya están por separado
            continue
        rels[r.id] = {"tags": tg, "vias": vias}
    print(f"      {len(rels)} relaciones de senderismo ({time.time() - t0:.0f} s)", flush=True)
    necesarias = {w for r in rels.values() for w in r["vias"]}
    geom: dict[int, list[tuple[float, float]]] = {}
    proc = (
        osmium.FileProcessor(str(pbf), osmium.osm.NODE | osmium.osm.WAY)
        .with_locations()
        .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
        .with_filter(osmium.filter.IdFilter(necesarias))
    )
    for w in proc:
        try:
            geom[w.id] = [(n.lon, n.lat) for n in w.nodes]
        except osmium.InvalidLocationError:
            continue
    print(f"      {len(geom)} vías con geometría ({time.time() - t0:.0f} s)", flush=True)
    rutas = []
    for rid, r in rels.items():
        tg = r["tags"]
        lineas = [geom[w] for w in r["vias"] if w in geom]
        if not lineas:
            continue
        nombre = tg.get("name") or tg.get("name:es")
        ref = tg.get("ref")
        if not nombre and not ref:
            continue
        # el orden de los miembros suele seguir el sentido oficial (de «from» a «to»)
        primera, ultima = lineas[0], lineas[-1]
        rutas.append(
            {
                "sentido": (primera[len(primera) // 2], ultima[len(ultima) // 2]) if len(lineas) > 1 else None,
                "id": f"osm-{rid}",
                "osm": rid,
                "fuente": "osm",
                "nombre": nombre,
                "ref": ref,
                "red": tg.get("network"),
                "operador": tg.get("operator"),
                "web": tg.get("website") or tg.get("url"),
                "desde": tg.get("from"),
                "hasta": tg.get("to"),
                "descripcion": tg.get("description"),
                "circular_tag": tg.get("roundtrip"),
                "wikidata": tg.get("wikidata"),
                "tipo": tipo_ruta(ref, nombre, tg.get("network"), tg),
                "tramos": partes_unidas(lineas),
            }
        )
    return rutas
