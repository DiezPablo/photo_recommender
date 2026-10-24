"""
Contaminación lumínica de un punto a partir del Atlas mundial del brillo
artificial del cielo de David Lorenz (2025, datos VIIRS), publicado en teselas PNG gratuitas:
https://djlorenz.github.io/astronomy/lp/

Cada color del atlas es una zona (0, 1a, 1b … 7b) con un rango de brillo en el cénit
(mag/arcsec²). De ahí damos un Bortle *aproximado*: el propio autor recuerda que su mapa mide
el brillo en el cénit y que Bortle es una escala visual de todo el cielo, así que la web lo
presenta como "≈ Bortle".

Las teselas se descargan una vez y se guardan en cache/lp/ (cada una cubre ~5,6° de longitud).
"""

from __future__ import annotations

import io
import math
from pathlib import Path

import requests

from rasante.comun.red import USER_AGENT

URL_TESELA = "https://djlorenz.github.io/astronomy/image_tiles/tiles2025/tile_{z}_{x}_{y}.png"
Z = 6  # zoom nativo de las teselas de 1024 px (≈ 1/120° de resolución)
TAM = 1024
CACHE = Path("cache") / "lp"

# color RGB → (zona, brillo en el cénit mag/arcsec² (centro del rango), Bortle aproximado)
PALETA = {
    (0, 0, 0): ("0", 22.0, 1),
    (34, 34, 34): ("1a", 21.96, 1),
    (66, 66, 66): ("1b", 21.91, 2),
    (20, 47, 114): ("2a", 21.85, 2),
    (33, 84, 216): ("2b", 21.75, 3),
    (15, 87, 20): ("3a", 21.6, 4),
    (31, 161, 42): ("3b", 21.38, 4),
    (110, 100, 30): ("4a", 21.08, 5),
    (184, 166, 37): ("4b", 20.7, 5),
    (191, 100, 30): ("5a", 20.25, 6),
    (253, 150, 80): ("5b", 19.76, 7),
    (251, 90, 73): ("6a", 19.22, 7),
    (251, 153, 138): ("6b", 18.66, 8),
    (160, 160, 160): ("7a", 18.09, 8),
    (242, 242, 242): ("7b", 17.5, 9),
}
DESCRIPCION_ZONA = {
    "0": "cielo prístino",
    "1": "cielo muy oscuro",
    "2": "cielo oscuro rural",
    "3": "rural con algo de resplandor",
    "4": "transición rural-periurbano",
    "5": "periurbano",
    "6": "urbano",
    "7": "centro de ciudad",
}

_teselas: dict[tuple[int, int], object] = {}


def _tesela(x: int, y: int):
    from PIL import Image

    if (x, y) in _teselas:
        return _teselas[(x, y)]
    f = CACHE / f"tile_{Z}_{x}_{y}.png"
    if not f.exists():
        r = requests.get(URL_TESELA.format(z=Z, x=x, y=y), timeout=60, headers={"User-Agent": USER_AGENT})
        if r.status_code == 404:
            _teselas[(x, y)] = None  # mar abierto o fuera del dominio del atlas
            return None
        r.raise_for_status()
        CACHE.mkdir(parents=True, exist_ok=True)
        f.write_bytes(r.content)
    img = Image.open(io.BytesIO(f.read_bytes())).convert("RGB")
    _teselas[(x, y)] = img
    return img


def _pixel(lat: float, lon: float) -> tuple[int, int, int, int]:
    n = 2**Z
    fx = (lon + 180) / 360 * n
    fy = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    x, y = int(fx), int(fy)
    return x, y, min(TAM - 1, int((fx - x) * TAM)), min(TAM - 1, int((fy - y) * TAM))


def _color_mas_cercano(rgb) -> tuple:
    return min(PALETA, key=lambda c: sum((a - b) ** 2 for a, b in zip(c, rgb, strict=True)))


def contaminacion(lat: float, lon: float, radio_px: int = 1) -> dict | None:
    """Zona del atlas, brillo del cielo y Bortle aproximado del punto. Toma la zona más
    frecuente en un cuadrado de (2·radio+1)² píxeles (~1,5 km) para no depender de un píxel."""
    x, y, px, py = _pixel(lat, lon)
    img = _tesela(x, y)
    if img is None:
        return None
    votos: dict[tuple, int] = {}
    for dx in range(-radio_px, radio_px + 1):
        for dy in range(-radio_px, radio_px + 1):
            cx, cy = min(TAM - 1, max(0, px + dx)), min(TAM - 1, max(0, py + dy))
            c = _color_mas_cercano(img.getpixel((cx, cy)))
            votos[c] = votos.get(c, 0) + 1
    centro = _color_mas_cercano(img.getpixel((px, py)))
    # la zona del propio punto gana los empates
    color = max(votos, key=lambda c: (votos[c], c == centro))
    zona, sqm, bortle = PALETA[color]
    return {"zona": zona, "sqm": sqm, "bortle": bortle, "descripcion": DESCRIPCION_ZONA[zona[0]]}


def _zona_num(zona: str) -> float:
    """'4b' → 4.5, '0' → 0."""
    return float(zona[0]) + (0.5 if zona.endswith("b") else 0.0)


def cupula(lat: float, lon: float, azimut: float, distancias=(10, 20, 35, 50, 75)) -> dict | None:
    """Cúpula de luz de ciudades en una dirección (la del núcleo de la Vía Láctea o el sur): la zona
    más brillante del atlas a lo largo de esa dirección, descontando ~1 zona cada 20 km (la cúpula
    de Madrid se ve desde la sierra a 50 km, pero baja sobre el horizonte). None si no destaca sobre
    el cielo del propio spot."""
    from rasante.cielo.astro import punto_destino  # import diferido: astro no depende de este módulo

    local = contaminacion(lat, lon)
    base = _zona_num(local["zona"]) if local else 0.0
    mejor = None
    for d in distancias:
        la, lo = punto_destino(lat, lon, azimut, d)
        c = contaminacion(la, lo, radio_px=2)
        if not c:
            continue
        efectiva = _zona_num(c["zona"]) - d / 20
        if mejor is None or efectiva > mejor[0]:
            mejor = (efectiva, c["zona"], d)
    if mejor is None or mejor[0] < base + 0.5 or mejor[0] < 4.5:
        return None
    return {"zona": mejor[1], "km": mejor[2], "efectiva": round(mejor[0], 1)}
