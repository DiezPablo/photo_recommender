"""Territorio: provincia y comunidad autónoma de un punto, y descarte de puntos fuera de España.

Recursos (rasante/recursos): polígonos de provincias del IGN simplificados y países vecinos de Natural Earth.
"""

from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

RECURSOS = Path(__file__).resolve().parent.parent / "recursos"
PROVINCIAS = RECURSOS / "provincias.geojson"
VECINOS = RECURSOS / "vecinos.geojson"


# Comunidad autónoma de cada provincia por su código INE (01-52). Se usa siempre esta tabla: el fichero
# de provincias de origen numeraba las comunidades de otra forma y las cruzó mal (Asturias salía «Ceuta»).
CCAA_POR_PROVINCIA = {
    **dict.fromkeys(["04", "11", "14", "18", "21", "23", "29", "41"], "Andalucía"),
    **dict.fromkeys(["22", "44", "50"], "Aragón"),
    "33": "Principado de Asturias",
    "07": "Illes Balears",
    **dict.fromkeys(["35", "38"], "Canarias"),
    "39": "Cantabria",
    **dict.fromkeys(["05", "09", "24", "34", "37", "40", "42", "47", "49"], "Castilla y León"),
    **dict.fromkeys(["02", "13", "16", "19", "45"], "Castilla-La Mancha"),
    **dict.fromkeys(["08", "17", "25", "43"], "Cataluña"),
    **dict.fromkeys(["03", "12", "46"], "Comunitat Valenciana"),
    **dict.fromkeys(["06", "10"], "Extremadura"),
    **dict.fromkeys(["15", "27", "32", "36"], "Galicia"),
    "28": "Comunidad de Madrid",
    "30": "Región de Murcia",
    "31": "Comunidad Foral de Navarra",
    **dict.fromkeys(["01", "20", "48"], "País Vasco"),
    "26": "La Rioja",
    "51": "Ceuta",
    "52": "Melilla",
}


# Nombres de provincia tal como vienen en rasante/recursos/provincias.geojson
_CCAA_POR_NOMBRE = {
    "Illes Balears": "Illes Balears",
    "Asturias": "Principado de Asturias",
    "A Coruña": "Galicia",
    "Girona": "Cataluña",
    "Las Palmas": "Canarias",
    "Pontevedra": "Galicia",
    "Santa Cruz de Tenerife": "Canarias",
    "Cantabria": "Cantabria",
    "Málaga": "Andalucía",
    "Almería": "Andalucía",
    "Murcia": "Región de Murcia",
    "Albacete": "Castilla-La Mancha",
    "Ávila": "Castilla y León",
    "Araba/Álava": "País Vasco",
    "Badajoz": "Extremadura",
    "Alacant/Alicante": "Comunitat Valenciana",
    "Ourense": "Galicia",
    "Barcelona": "Cataluña",
    "Burgos": "Castilla y León",
    "Cáceres": "Extremadura",
    "Cádiz": "Andalucía",
    "Castelló/Castellón": "Comunitat Valenciana",
    "Ciudad Real": "Castilla-La Mancha",
    "Jaén": "Andalucía",
    "Córdoba": "Andalucía",
    "Cuenca": "Castilla-La Mancha",
    "Granada": "Andalucía",
    "Guadalajara": "Castilla-La Mancha",
    "Gipuzkoa/Guipúzcoa": "País Vasco",
    "Huelva": "Andalucía",
    "Huesca": "Aragón",
    "León": "Castilla y León",
    "Lleida": "Cataluña",
    "La Rioja": "La Rioja",
    "Soria": "Castilla y León",
    "Navarra": "Comunidad Foral de Navarra",
    "Ceuta": "Ceuta",
    "Lugo": "Galicia",
    "Madrid": "Comunidad de Madrid",
    "Palencia": "Castilla y León",
    "Salamanca": "Castilla y León",
    "Segovia": "Castilla y León",
    "Sevilla": "Andalucía",
    "Toledo": "Castilla-La Mancha",
    "Tarragona": "Cataluña",
    "Teruel": "Aragón",
    "València/Valencia": "Comunitat Valenciana",
    "Valladolid": "Castilla y León",
    "Bizkaia/Vizcaya": "País Vasco",
    "Zamora": "Castilla y León",
    "Zaragoza": "Aragón",
    "Melilla": "Melilla",
}


def ccaa_de(provincia: str | None, ccaa: str | None = None) -> str | None:
    """Comunidad correcta a partir del nombre de la provincia (tal como viene en rasante/recursos/provincias.geojson)."""
    return _CCAA_POR_NOMBRE.get(provincia or "", ccaa)


class Provincias:
    def __init__(self, ruta: Path = PROVINCIAS, vecinos: Path = VECINOS):
        fs = json.loads(ruta.read_text())["features"]
        self.geoms = [shape(f["geometry"]) for f in fs]
        self.props = [f["properties"] for f in fs]
        self.arbol = STRtree(self.geoms)
        # Los polígonos de provincias están simplificados y en la raya se meten en Portugal (Marvão salía
        # en Cáceres): fuera lo que cae dentro de un país vecino a más de ~200 m de su borde.
        self.fuera = [shape(f["geometry"]).buffer(-0.002) for f in json.loads(vecinos.read_text())["features"]]

    def de(self, lat: float, lon: float) -> dict | None:
        p = Point(lon, lat)
        if any(g.contains(p) for g in self.fuera):
            return None
        for i in self.arbol.query(p):
            if self.geoms[i].contains(p):
                return self.props[i]
        # en la costa el polígono simplificado puede quedarse corto: la provincia a menos de 1,5 km
        cerca = self.arbol.query(p.buffer(0.015))
        if len(cerca):
            i = min(cerca, key=lambda j: self.geoms[j].distance(p))
            return self.props[i]
        return None
