"""Nombres de spots: limpieza de títulos y descarte de nombres que no identifican un lugar."""

from __future__ import annotations

import re


def limpiar_nombre(t: str) -> str:
    """Título de foto → nombre de spot: sin ids de Flickr, fechas, numeración ni 'panoramio'."""
    t = re.sub(r"\((?:[^()]*\d{4}[^()]*|\d+)\)", " ", t)  # (6495112213), (2 de mayo de 2015, …)
    t = re.sub(r"\b(?:19|20)\d\d[-_.]\d\d[-_.]\d\d\b", " ", t)  # 2011-06-05
    t = re.sub(r"(?i)\s*-?\s*panoramio\b.*$", " ", t)
    t = re.sub(r"(?i)\b(?:retouched|cropped|by[- ]\S+|img|dsc|p\d{6,})\b", " ", t)
    t = re.sub(r"[_]+", " ", t)
    t = re.sub(r"(?<=[a-záéíóúñ])(?=[A-ZÁÉÍÓÚÑ][a-záéíóúñ])", " ", t)  # LaSierra → La Sierra
    t = re.sub(r"(?:\s*[-–]\s*|\s+)\d{1,3}$", "", t.strip())  # " - 01", " 09", "Pirón2"
    t = re.sub(r"(?<=[a-záéíóúñ])\d{1,2}$", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" -–,.")
    if t.isupper():
        t = t.title().replace(" De ", " de ").replace(" Del ", " del ").replace(" La ", " la ").replace(" El ", " el ")
    return t[:70]


# Nombres que no identifican un lugar (OSM): «Mirador», «Mural», «Picnic», «Begiratokia» (mirador en euskera)…
NOMBRE_GENERICO = re.compile(
    r"^(?:(?:el|la|los|las)\s+)?(?:mirador(?:\s+(?:del?\s+)?(?:r[ií]o|valle|mar|pueblo|lago|embalse))?|miradoiro|miranda|"
    r"begiratoki(?:a)?|talaia|viewpoint|view\s*point|vista|vistas|panor[aá]mica|panorama|mural|picnic|merendero|"
    r"spotting|bandera|cascada|salto|playa|cala|faro|cumbre|pico|caseta|balc[oó]n(?:\s+mirador)?|"
    r"paisaje(?:\s+din[aá]mico)?|torre|cruz|ermita|fuente|puente)$",
    re.I,
)


# Calles, aparcamientos, terrazas de bar…: no son spots de paisaje
NOMBRE_EXCLUIR = re.compile(r"\b(?:calle|avenida|avda|parking|aparcamiento|terraza|bar|restaurante|hotel)\b", re.I)


def nombre_valido(nombre: str) -> bool:
    n = re.sub(r"\s+", " ", str(nombre)).strip(" .,-")
    return len(n) >= 4 and not NOMBRE_GENERICO.match(n) and not NOMBRE_EXCLUIR.search(n)
