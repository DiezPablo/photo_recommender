"""comun.py — Utilidades compartidas por el pipeline."""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path

USER_AGENT = ("spots-paisaje/0.3 (https://github.com/DiezPablo/photo_recommender; "
              "proyecto personal no comercial)")


def id_spot(nombre: str, lat: float, lon: float) -> str:
    """Identificador estable y legible para URLs: 'mirador-de-la-barranca-3f9a'."""
    base = unicodedata.normalize("NFKD", nombre if isinstance(nombre, str) and nombre else "spot").encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:48].strip("-") or "spot"
    h = hashlib.sha1(f"{lat:.4f},{lon:.4f}".encode()).hexdigest()[:4]
    return f"{base}-{h}"


def limpiar_json(v):
    """Convierte NaN/inf y tipos numpy en valores JSON válidos (null o números nativos)."""
    if isinstance(v, dict):
        return {k: limpiar_json(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [limpiar_json(x) for x in v]
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):   # numpy escalares
        v = v.item()
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def escribir_json(ruta: Path, datos, indent: int | None = None) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(limpiar_json(datos), ensure_ascii=False, indent=indent,
                               allow_nan=False, separators=None if indent else (",", ":")))


# Comunidad autónoma de cada provincia por su código INE (01-52). Se usa siempre esta tabla: el fichero
# de provincias de origen numeraba las comunidades de otra forma y las cruzó mal (Asturias salía «Ceuta»).
CCAA_POR_PROVINCIA = {
    **dict.fromkeys(["04", "11", "14", "18", "21", "23", "29", "41"], "Andalucía"),
    **dict.fromkeys(["22", "44", "50"], "Aragón"),
    "33": "Principado de Asturias", "07": "Illes Balears",
    **dict.fromkeys(["35", "38"], "Canarias"),
    "39": "Cantabria",
    **dict.fromkeys(["05", "09", "24", "34", "37", "40", "42", "47", "49"], "Castilla y León"),
    **dict.fromkeys(["02", "13", "16", "19", "45"], "Castilla-La Mancha"),
    **dict.fromkeys(["08", "17", "25", "43"], "Cataluña"),
    **dict.fromkeys(["03", "12", "46"], "Comunitat Valenciana"),
    **dict.fromkeys(["06", "10"], "Extremadura"),
    **dict.fromkeys(["15", "27", "32", "36"], "Galicia"),
    "28": "Comunidad de Madrid", "30": "Región de Murcia", "31": "Comunidad Foral de Navarra",
    **dict.fromkeys(["01", "20", "48"], "País Vasco"),
    "26": "La Rioja", "51": "Ceuta", "52": "Melilla",
}


# Nombres de provincia tal como vienen en datos_base/provincias.geojson
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
    """Comunidad correcta a partir del nombre de la provincia (tal como viene en datos_base/provincias.geojson)."""
    return _CCAA_POR_NOMBRE.get(provincia or "", ccaa)
