"""Piezas comunes de los modelos de nota: la nota con su desglose y el acumulador de factores."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import pairwise


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def valor(d, clave, defecto=0.0) -> float:
    """Valor numérico de un dict o Series, con defecto si falta o es NaN."""
    try:
        v = d.get(clave, defecto)
    except AttributeError:
        return defecto
    if v is None:
        return defecto
    try:
        v = float(v)
    except (TypeError, ValueError):
        return defecto
    return defecto if math.isnan(v) else v


def por_tramos(x: float, puntos: list[tuple[float, float]]) -> float:
    """Interpolación lineal por tramos: puntos (x, y) ordenados por x."""
    if x <= puntos[0][0]:
        return puntos[0][1]
    for (x0, y0), (x1, y1) in pairwise(puntos):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return puntos[-1][1]


@dataclass
class Nota:
    base: float
    texto_base: str
    factores: list[tuple[str, float]] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)  # datos del modelo útiles para la web

    def suma(self, texto: str, puntos: float, minimo: float = 0.05):
        if abs(puntos) >= minimo:
            self.factores.append((texto, round(puntos, 1)))

    @property
    def bruta(self) -> float:
        return self.base + sum(p for _, p in self.factores)

    @property
    def valor(self) -> float:
        return round(clamp(self.bruta, 0, 10), 1)

    def a_dict(self) -> dict:
        d = {
            "nota": self.valor,
            "desglose": [{"texto": self.texto_base, "puntos": round(self.base, 1)}]
            + [{"texto": t, "puntos": p} for t, p in self.factores],
            "avisos": self.avisos,
        }
        if self.extra:
            d["modelo"] = self.extra
        return d


class Acumulador:
    """Explica como sumas una nota que se calcula multiplicando: cada paso anota cuánto cambia."""

    def __init__(self, nota: Nota):
        self.n = nota

    def paso(self, texto: str, antes: float, despues: float, minimo: float = 0.05) -> float:
        self.n.suma(texto, despues - antes, minimo)
        return despues
