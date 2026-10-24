"""Métricas de una ruta: desnivel con el DEM, tiempo por el método MIDE, esfuerzo estimado y tipo de sendero."""

from __future__ import annotations

import re


def desnivel(alturas: list[float]) -> tuple[float, float]:
    """Subida y bajada acumuladas. Se suaviza (media de 5 puntos, ~150 m) y se ignoran oscilaciones de
    menos de 3 m: el DEM a 30 m tiene ruido que inflaría el desnivel."""
    if len(alturas) < 2:
        return 0.0, 0.0
    k = 2
    suave = [
        sum(alturas[max(0, i - k) : i + k + 1]) / len(alturas[max(0, i - k) : i + k + 1]) for i in range(len(alturas))
    ]
    subida = bajada = 0.0
    ref = suave[0]
    for h in suave[1:]:
        if h - ref >= 3:
            subida += h - ref
            ref = h
        elif ref - h >= 3:
            bajada += ref - h
            ref = h
    return subida, bajada


def tiempo_mide(km: float, subida: float, bajada: float) -> float:
    """Horas de marcha según el método MIDE (sin paradas): 4 km/h en llano, 400 m/h subiendo y 600 m/h
    bajando; el tiempo es el mayor de horizontal y vertical más la mitad del menor."""
    th = km / 4
    tv = subida / 400 + bajada / 600
    return max(th, tv) + min(th, tv) / 2


def dificultad(horas: float, subida: float, alt_max: float) -> str:
    """Esfuerzo estimado (no es la valoración MIDE oficial, que pide conocer el terreno)."""
    puntos = horas + subida / 500 + (1 if alt_max > 2000 else 0)
    if puntos < 3:
        return "fácil"
    if puntos < 6:
        return "moderada"
    if puntos < 10:
        return "difícil"
    return "muy difícil"


def tipo_ruta(ref: str | None, nombre: str | None, red: str | None, extra: dict) -> str:
    texto = f"{ref or ''} {nombre or ''}"
    if extra.get("pilgrimage") == "yes" or re.search(
        r"\bcamino de santiago|\bcamí de sant jaume|\bruta jacobea|\bvía de la plata\b", texto, re.I
    ):
        return "Camino de Santiago"
    if re.search(r"\bE[- ]?\d{1,2}\b", ref or "") or red == "iwn":
        return "Europeo"
    if re.search(r"\bGR[- ]?\d", texto, re.I):
        return "GR"
    if re.search(r"\bPR[- ]", texto, re.I):
        return "PR"
    if re.search(r"\bSL[- ]", texto, re.I):
        return "SL"
    if re.search(r"camino natural", texto, re.I):
        return "Camino Natural"
    if re.search(r"v[ií]a verde", texto, re.I):
        return "Vía Verde"
    return "Sendero"
