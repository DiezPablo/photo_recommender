"""
horizonte.py — Horizonte del terreno de cada spot a partir de un modelo digital de elevaciones.

Fuente: teselas "Terrarium" de Mapzen/AWS (Open Data, gratuitas y sin clave):
https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png  (altura = R·256 + G + B/256 − 32768 m)

Para cada spot se calcula el ángulo del horizonte (grados sobre la horizontal) cada 2° de azimut
hasta 60 km, con curvatura terrestre y refracción. Sirve para saber:
  - si el sol se pone (o sale) a la vista o detrás de una montaña, y a qué hora desaparece de verdad;
  - hacia dónde está abierta la vista;
  - si el núcleo de la Vía Láctea o la luna llegan a asomar sobre las crestas.
Se calcula una vez por spot (en el descubrimiento) y se guarda en el geojson.
"""
from __future__ import annotations

import io
import math
import os
from pathlib import Path

import numpy as np
import requests

URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
CACHE = Path("cache") / "dem"
USER_AGENT = os.environ.get(
    "USER_AGENT", "spots-paisaje/0.3 (https://github.com/DiezPablo/photo_recommender; proyecto personal no comercial)")
R_TIERRA = 6_371_000.0
K_REFRACCION = 0.13          # coeficiente de refracción terrestre habitual
PASO_AZ = 2                  # grados entre azimuts
OJO_M = 2.0                  # altura de la cámara sobre el suelo
# (distancia máxima en m, zoom): cerca más detalle, lejos basta menos
ZOOMS = ((6_000, 12), (25_000, 11), (60_000, 10))

_teselas: dict[tuple[int, int, int], np.ndarray | None] = {}


def _tesela(z: int, x: int, y: int) -> np.ndarray | None:
    from PIL import Image
    k = (z, x, y)
    if k in _teselas:
        return _teselas[k]
    f = CACHE / f"{z}_{x}_{y}.png"
    if not f.exists():
        r = None
        for intento in range(4):
            try:
                r = requests.get(URL.format(z=z, x=x, y=y), timeout=60, headers={"User-Agent": USER_AGENT})
                break
            except requests.RequestException:
                continue
        if r is None or r.status_code in (403, 404):
            _teselas[k] = None
            return None
        r.raise_for_status()
        CACHE.mkdir(parents=True, exist_ok=True)
        f.write_bytes(r.content)
    a = np.asarray(Image.open(io.BytesIO(f.read_bytes())).convert("RGB"), dtype=np.float32)
    h = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    h[h < -500] = 0          # agujeros: mar
    _teselas[k] = h
    return h


def _xy(lat: float, lon: float, z: int) -> tuple[float, float]:
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def altura(lat: float, lon: float, z: int = 12) -> float:
    """Altura del terreno (m), interpolación bilineal."""
    fx, fy = _xy(lat, lon, z)
    px, py = fx * 256 - 0.5, fy * 256 - 0.5
    x0, y0 = math.floor(px), math.floor(py)
    vals = []
    for dy in (0, 1):
        for dx in (0, 1):
            gx, gy = x0 + dx, y0 + dy
            t = _tesela(z, gx // 256, gy // 256)
            vals.append(0.0 if t is None else float(t[gy % 256, gx % 256]))
    wx, wy = px - x0, py - y0
    return (vals[0] * (1 - wx) * (1 - wy) + vals[1] * wx * (1 - wy)
            + vals[2] * (1 - wx) * wy + vals[3] * wx * wy)


def _destino(lat: float, lon: float, az: float, d: float) -> tuple[float, float]:
    la1, lo1, b, ang = math.radians(lat), math.radians(lon), math.radians(az), d / R_TIERRA
    la2 = math.asin(math.sin(la1) * math.cos(ang) + math.cos(la1) * math.sin(ang) * math.cos(b))
    lo2 = lo1 + math.atan2(math.sin(b) * math.sin(ang) * math.cos(la1), math.cos(ang) - math.sin(la1) * math.sin(la2))
    return math.degrees(la2), math.degrees(lo2)


def _distancias() -> list[float]:
    d, out = 60.0, []
    while d <= ZOOMS[-1][0]:
        out.append(d)
        d *= 1.08 if d < 2000 else 1.06
    return out


def elevacion_observador(lat: float, lon: float) -> float:
    """Altura del punto de vista: el máximo en un radio de ~60 m (los miradores de OSM a veces
    quedan unos metros por debajo de la cresta y el modelo de 30-60 m suaviza las cimas)."""
    h = [altura(lat, lon)]
    for az in range(0, 360, 60):
        h.append(altura(*_destino(lat, lon, az, 60)))
    return max(h)


def perfil(lat: float, lon: float) -> dict:
    """{"elevacion": m, "angulos": [grados·10 cada PASO_AZ°, desde el norte hacia el este]}."""
    h0 = elevacion_observador(lat, lon) + OJO_M
    ds = _distancias()
    angulos = []
    for az in range(0, 360, PASO_AZ):
        maximo = -5.0
        for d in ds:
            z = next(zz for dmax, zz in ZOOMS if d <= dmax)
            h = altura(*_destino(lat, lon, az, d), z=z)
            caida = d * d / (2 * R_TIERRA) * (1 - K_REFRACCION)
            ang = math.degrees(math.atan2(h - h0 - caida, d))
            if ang > maximo:
                maximo = ang
        angulos.append(int(round(maximo * 10)))
    return {"elevacion": round(h0 - OJO_M), "angulos": angulos}


# ---------------------------------------------------------- consultas ----
def angulo(perfil_: dict | None, az: float, ancho: float = 0.0) -> float | None:
    """Ángulo del horizonte (grados) hacia el azimut az. Con ancho > 0, el máximo en az ± ancho/2."""
    if not perfil_ or not perfil_.get("angulos"):
        return None
    a = perfil_["angulos"]
    paso = 360 / len(a)
    if ancho <= 0:
        i = az / paso
        i0 = int(math.floor(i)) % len(a)
        w = i - math.floor(i)
        return (a[i0] * (1 - w) + a[(i0 + 1) % len(a)] * w) / 10
    ini, fin = az - ancho / 2, az + ancho / 2
    idx = {int(round(x / paso)) % len(a) for x in np.arange(ini, fin + paso / 2, paso)}
    return max(a[i] for i in idx) / 10


def apertura(perfil_: dict | None, umbral: float = 2.0) -> list[tuple[int, int]]:
    """Sectores (azimut inicial, final) con el horizonte por debajo de `umbral` grados: hacia dónde
    está abierta la vista."""
    if not perfil_ or not perfil_.get("angulos"):
        return []
    a = perfil_["angulos"]
    paso = 360 // len(a)
    libre = [x / 10 < umbral for x in a]
    if all(libre):
        return [(0, 360)]
    inicio = libre.index(False)   # empezar en un tramo bloqueado para no partir sectores en el norte
    sectores, ini = [], None
    for k in range(1, len(a) + 1):
        i = (inicio + k) % len(a)
        if libre[i] and ini is None:
            ini = i
        elif not libre[i] and ini is not None:
            sectores.append((ini * paso, i * paso))
            ini = None
    if ini is not None:
        sectores.append((ini * paso, inicio * paso))
    return [s for s in sectores if (s[1] - s[0]) % 360 >= 10]
