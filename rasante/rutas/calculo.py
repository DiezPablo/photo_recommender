"""Cálculo de cada ruta: recorrido, perfil y desnivel, tiempo, ubicación y trazados codificados."""

from __future__ import annotations

import math

import requests

from rasante.comun.territorio import ccaa_de
from rasante.terreno import horizonte

from .geometria import codificar, longitud_m, metros, muestrear, ordenar_tramos, orientar, simplificar
from .metricas import desnivel, dificultad, tiempo_mide

PASO_M = 30  # muestreo del perfil


SIMPLIFICAR_M = 10  # trazado de la ficha


SIMPLIFICAR_MAPA_M = 60  # trazado del mapa general


MAX_PERFIL = 160  # puntos del perfil que se guardan


def completar(r: dict, provincias) -> dict | None:
    """Recorrido, métricas y ubicación. None si la ruta no sirve (muy corta, fuera de España…)."""
    partes = ordenar_tramos(r["tramos"])
    if not partes:
        return None
    km = sum(longitud_m(t) for t in partes) / 1000
    if km < 0.5 or km > 1500:
        return None
    partes = orientar(partes, r.get("sentido"))
    camino = [p for t in partes for p in t]
    ini, fin = camino[0], camino[-1]
    info = provincias.de(ini[1], ini[0]) or provincias.de(fin[1], fin[0])
    if not info:
        mitad = camino[len(camino) // 2]
        info = provincias.de(mitad[1], mitad[0])
    if not info:
        return None
    # perfil: en rutas muy largas basta un punto cada ~100 m
    pts = muestrear([simplificar(t, 5) for t in partes], PASO_M if km < 60 else 100)
    alturas = []
    for lon, lat, _ in pts:
        try:
            alturas.append(horizonte.altura(lat, lon, 12 if km < 60 else 11))
        except (requests.RequestException, TypeError):
            alturas.append(float("nan"))
    validas = [h for h in alturas if h == h]
    if len(validas) < max(2, len(alturas) // 2):
        subida = bajada = 0.0
        alt_max = alt_min = None
        perfil = []
    else:
        ult = validas[0]
        alturas = [(ult := h) if h == h else ult for h in alturas]
        subida, bajada = desnivel(alturas)
        alt_max, alt_min = max(alturas), min(alturas)
        paso = max(1, math.ceil(len(pts) / MAX_PERFIL))
        perfil = [[round(pts[i][2] / 1000, 2), round(alturas[i])] for i in range(0, len(pts), paso)]
        if perfil[-1][0] != round(pts[-1][2] / 1000, 2):
            perfil.append([round(pts[-1][2] / 1000, 2), round(alturas[-1])])
    circular = r["circular_tag"] == "yes" or (r["circular_tag"] != "no" and metros(ini, fin) < 300)
    if circular:
        subida = bajada = max(subida, bajada)  # en una circular se sube lo que se baja
    horas = tiempo_mide(km, subida, bajada)
    xs, ys = [c[0] for c in camino], [c[1] for c in camino]
    nombre = r["nombre"] or r["ref"]
    return {
        "id": r["id"],
        "nombre": nombre,
        "ref": r["ref"] if r["ref"] and r["ref"] not in (nombre or "") else None,
        "tipo": r["tipo"],
        "fuente": r["fuente"],
        "osm": r.get("osm"),
        "oficial": r.get("oficial"),
        "web": r["web"],
        "operador": r["operador"],
        "desde": r["desde"],
        "hasta": r["hasta"],
        "descripcion": (r["descripcion"] or "")[:400] or None,
        "wikidata": r["wikidata"],
        "km": round(km, 1),
        "subida": round(subida),
        "bajada": round(bajada),
        "alt_max": None if alt_max is None else round(alt_max),
        "alt_min": None if alt_min is None else round(alt_min),
        "horas": round(horas, 1),
        "dificultad": dificultad(horas, subida, alt_max or 0),
        "circular": circular,
        "provincia": info["provincia"],
        "ccaa": ccaa_de(info["provincia"], info.get("ccaa")),
        "inicio": [round(ini[1], 5), round(ini[0], 5)],
        "fin": [round(fin[1], 5), round(fin[0], 5)],
        "bbox": [round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)],
        "perfil": perfil,
        # trazado por trozos (los huecos no se dibujan)
        "linea": [codificar(simplificar(t, SIMPLIFICAR_M)) for t in partes],
        "linea_mapa": [
            codificar(simplificar(t, SIMPLIFICAR_MAPA_M if km < 60 else 200))
            for t in partes
            if longitud_m(t) > 50 or len(partes) == 1
        ],
    }
