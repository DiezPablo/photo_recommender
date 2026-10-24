"""Geometría de los recorridos: distancias, unión y orden de tramos, sentido de marcha, simplificación,
muestreo y codificación del trazado («encoded polyline»)."""

from __future__ import annotations

import math
from itertools import pairwise

import requests
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge

from rasante.terreno import horizonte

M_POR_GRADO = 111_320.0


def metros(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distancia aproximada (m) entre dos puntos (lon, lat): equirrectangular, sobra para tramos cortos."""
    x = (b[0] - a[0]) * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot(x, b[1] - a[1]) * M_POR_GRADO


def longitud_m(coords: list[tuple[float, float]]) -> float:
    return sum(metros(coords[i], coords[i + 1]) for i in range(len(coords) - 1))


Camino = list[list[tuple[float, float]]]  # recorrido: trozos continuos, en orden de marcha


UNIR_M = 30  # trozos a menos de esto se consideran continuos


def ordenar_tramos(tramos: Camino) -> Camino:
    """Ordena los tramos de una ruta como un recorrido: empieza por el extremo más aislado y va enlazando
    el tramo más cercano (dándole la vuelta si hace falta). Los que empiezan donde acaba el anterior
    (< 30 m) se funden; los demás quedan como trozos separados: el hueco no se recorre ni se dibuja."""
    pendientes = [list(t) for t in tramos if len(t) >= 2]
    if not pendientes:
        return []

    def aislamiento(t, i):
        p = t[i]
        return min((metros(p, o[j]) for o in pendientes if o is not t for j in (0, -1)), default=0)

    t0, extremo = max(((t, i) for t in pendientes for i in (0, -1)), key=lambda x: aislamiento(*x))
    pendientes.remove(t0)
    partes = [list(t0) if extremo == 0 else list(t0[::-1])]
    while pendientes:
        fin = partes[-1][-1]
        t, d = min(((t, d) for t in pendientes for d in (0, -1)), key=lambda x: metros(fin, x[0][x[1]]))
        pendientes.remove(t)
        siguiente = t if d == 0 else t[::-1]
        if metros(fin, siguiente[0]) < UNIR_M:
            partes[-1].extend(siguiente[1:])
        else:
            partes.append(list(siguiente))
    return partes


def orientar(partes: Camino, sentido) -> Camino:
    """Sentido de marcha. Con (principio, final) de la fuente (orden de los miembros de la relación o de
    la línea oficial), el recorrido empieza por el extremo más cercano al principio. Si no se sabe, se
    empieza por el extremo más bajo: en montaña las rutas lineales suelen subir desde el aparcamiento."""
    ini, fin = partes[0][0], partes[-1][-1]
    al_reves = [p[::-1] for p in partes[::-1]]
    if sentido:
        a, b = sentido
        if metros(a, b) > 200:
            return al_reves if metros(fin, a) + metros(ini, b) < metros(ini, a) + metros(fin, b) else partes
    if metros(ini, fin) < 300:
        return partes
    try:
        if horizonte.altura(fin[1], fin[0]) < horizonte.altura(ini[1], ini[0]) - 20:
            return al_reves
    except (requests.RequestException, TypeError):
        pass
    return partes


def partes_unidas(lineas: list[list[tuple[float, float]]]) -> list[list[tuple[float, float]]]:
    """Fusiona las vías de una relación en tramos continuos."""
    if not lineas:
        return []
    m = linemerge(MultiLineString([LineString(linea) for linea in lineas if len(linea) >= 2]))
    geoms = [m] if isinstance(m, LineString) else list(m.geoms)
    return [list(g.coords) for g in geoms if len(g.coords) >= 2]


def simplificar(coords: list[tuple[float, float]], tolerancia_m: float) -> list[tuple[float, float]]:
    if len(coords) < 3:
        return coords
    return list(LineString(coords).simplify(tolerancia_m / M_POR_GRADO, preserve_topology=False).coords)


def codificar(coords: list[tuple[float, float]], precision: int = 5) -> str:
    """Encoded polyline (algoritmo de Google): lat,lon con 5 decimales (~1 m), ~4 veces menos que JSON."""
    factor = 10**precision
    salida, plat, plon = [], 0, 0
    for lon, lat in coords:
        ilat, ilon = round(lat * factor), round(lon * factor)
        for v in (ilat - plat, ilon - plon):
            v = ~(v << 1) if v < 0 else v << 1
            while v >= 0x20:
                salida.append(chr((0x20 | (v & 0x1F)) + 63))
                v >>= 5
            salida.append(chr(v + 63))
        plat, plon = ilat, ilon
    return "".join(salida)


def muestrear(partes: Camino, paso_m: float) -> list[tuple[float, float, float]]:
    """Puntos cada `paso_m` metros a lo largo del recorrido: (lon, lat, distancia acumulada en m). Los
    huecos entre trozos no suman distancia."""
    puntos: list[tuple[float, float, float]] = []
    acum = 0.0
    for coords in partes:
        puntos.append((coords[0][0], coords[0][1], acum))
        resto = 0.0
        for a, b in pairwise(coords):
            d = metros(a, b)
            pos = paso_m - resto
            while pos <= d:
                f = pos / d
                puntos.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, acum + pos))
                pos += paso_m
            resto = d - (pos - paso_m)
            acum += d
        if puntos[-1][2] < acum:
            puntos.append((coords[-1][0], coords[-1][1], acum))
    return puntos
