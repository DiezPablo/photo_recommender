"""Puntos útiles de OpenStreetMap (nodos y áreas) leídos de un extracto PBF u OSM XML."""

from __future__ import annotations

import time
from pathlib import Path

ACCESO_FUERA = {"private", "no", "customers", "permit", "delivery"}
REFUGIOS = {"alpine_hut": "refugio guardado", "wilderness_hut": "refugio libre"}
ABRIGOS = {"basic_hut", "weather_shelter", "lean_to", "rock_shelter"}


def clasificar(tg: dict) -> tuple[str, str | None] | None:
    """(tipo, detalle) de un elemento de OSM, o None si no interesa."""
    if tg.get("access") in ACCESO_FUERA:
        return None
    amenity, tourism = tg.get("amenity"), tg.get("tourism")
    if tourism in REFUGIOS:
        return "refugio", REFUGIOS[tourism]
    if amenity == "shelter" and tg.get("shelter_type") in ABRIGOS:
        return "refugio", "abrigo"
    if amenity == "drinking_water" or (
        tg.get("drinking_water") == "yes" and (tg.get("natural") == "spring" or amenity == "fountain")
    ):
        return "fuente", "fuente" if tg.get("natural") != "spring" else "manantial"
    if tourism == "caravan_site":
        return "autocaravanas", None
    if tourism == "camp_site":
        return "camping", None
    if amenity == "parking" and tg.get("parking") not in ("underground", "multi-storey", "rooftop"):
        return "aparcamiento", None
    return None


def leer_puntos(fichero: Path) -> list[dict]:
    """Nodos y vías (en su centro) de los tipos que interesan."""
    import osmium

    t0 = time.time()
    puntos = []
    filtro = osmium.filter.KeyFilter("amenity", "tourism", "natural")
    proc = osmium.FileProcessor(str(fichero), osmium.osm.NODE | osmium.osm.WAY).with_locations().with_filter(filtro)
    for o in proc:
        tg = dict(o.tags)
        c = clasificar(tg)
        if not c:
            continue
        if o.is_node():
            lat, lon = o.location.lat, o.location.lon
        else:
            locs = [n.location for n in o.nodes if n.location.valid()]
            if not locs:
                continue
            lat = sum(x.lat for x in locs) / len(locs)
            lon = sum(x.lon for x in locs) / len(locs)
        puntos.append(
            {
                "tipo": c[0],
                "detalle": c[1],
                "nombre": tg.get("name"),
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "osm": f"{'node' if o.is_node() else 'way'}/{o.id}",
            }
        )
    print(f"      {len(puntos)} puntos útiles ({time.time() - t0:.0f} s)", flush=True)
    return puntos
