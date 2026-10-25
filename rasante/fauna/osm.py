"""Observatorios de fauna de OpenStreetMap, agrupados: en un humedal suele haber varios a pocos cientos de metros."""

from __future__ import annotations

import time
from pathlib import Path

from rasante.logistica.cercanos import km

AGRUPAR_KM = 0.7


PLACES = {"city", "town", "village", "hamlet"}
NOMBRE_KM = 8.0


def leer_observatorios(fichero: Path) -> list[dict]:
    """Observatorios y, para nombrar los que no tienen nombre, los núcleos de población (`place`)."""
    import osmium

    t0 = time.time()
    lista = []
    nucleos = []
    proc = (
        osmium.FileProcessor(str(fichero), osmium.osm.NODE | osmium.osm.WAY)
        .with_locations()
        .with_filter(osmium.filter.KeyFilter("leisure", "place"))
    )
    for o in proc:
        tg = dict(o.tags)
        if o.is_node() and tg.get("place") in PLACES and tg.get("name"):
            nucleos.append((o.location.lat, o.location.lon, tg["name"]))
            continue
        if tg.get("leisure") not in ("bird_hide", "wildlife_hide") or tg.get("access") in ("private", "no"):
            continue
        if o.is_node():
            lat, lon = o.location.lat, o.location.lon
        else:
            locs = [n.location for n in o.nodes if n.location.valid()]
            if not locs:
                continue
            lat, lon = sum(x.lat for x in locs) / len(locs), sum(x.lon for x in locs) / len(locs)
        lista.append(
            {
                "nombre": tg.get("name"),
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "osm": f"{'node' if o.is_node() else 'way'}/{o.id}",
                "accesible": tg.get("wheelchair") == "yes",
            }
        )
    print(f"      {len(lista)} observatorios ({time.time() - t0:.0f} s)", flush=True)
    for o in lista:
        o["cerca_de"] = nucleo_cercano(nucleos, o["lat"], o["lon"])
    return lista


def nucleo_cercano(nucleos: list[tuple[float, float, str]], lat: float, lon: float) -> str | None:
    """El pueblo más cercano a menos de NOMBRE_KM (para nombrar observatorios sin nombre en OSM)."""
    cerca = [(km((lat, lon), (la, lo)), n) for la, lo, n in nucleos if abs(la - lat) < 0.1 and abs(lo - lon) < 0.13]
    cerca = [x for x in cerca if x[0] <= NOMBRE_KM]
    return min(cerca)[1] if cerca else None


def agrupar(observatorios: list[dict]) -> list[dict]:
    """Un grupo por humedal o paraje: el nombre del primero con nombre y cuántos observatorios tiene."""
    grupos: list[dict] = []
    # primero los que tienen nombre, para que den nombre al grupo
    for o in sorted(observatorios, key=lambda x: x["nombre"] is None):
        g = next((g for g in grupos if km((g["lat"], g["lon"]), (o["lat"], o["lon"])) <= AGRUPAR_KM), None)
        if g:
            g["miembros"].append(o)
        else:
            grupos.append({**o, "miembros": [o]})
    for g in grupos:
        g["observatorios"] = len(g.pop("miembros"))
    return grupos
