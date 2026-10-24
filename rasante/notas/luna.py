"""Salida o puesta de la luna sobre el paisaje en el crepúsculo."""

from __future__ import annotations

from .base import Acumulador, Nota, clamp, por_tramos, valor
from .luz import PESO_CAMINO


# ============================================================ luna ====
def nota_luna(evento: dict | None, local: dict | None = None, camino: list[dict] | None = None) -> Nota:
    """Salida (o puesta) de la luna sobre el paisaje en el crepúsculo.

    evento: {"tipo", "hora" "HH:MM", "iluminacion" 0-1, "altura_sol" (°), "horizonte" (°), "azimut"}.
    local: nubes en el spot en ese momento; camino: nubes bajas hacia la luna (15-150 km).
    Lo buscado: luna casi llena, que aparece con el sol entre -6° y +2° (el paisaje aún tiene luz y la
    exposición se equilibra) y un horizonte limpio en su dirección."""
    if not evento:
        n = Nota(0.0, "Sin salida ni puesta de luna en el crepúsculo")
        return n
    ilum, hsol = evento["iluminacion"], evento["altura_sol"]
    accion = "Sale" if evento["tipo"] == "salida" else "Se pone"
    n = Nota(
        10.0, f"{accion} la luna a las {evento['hora']} hacia {evento['azimut']:.0f}°: luna llena en el crepúsculo"
    )
    a = Acumulador(n)
    total = 10.0
    total = a.paso(f"Luna al {ilum * 100:.0f} %", total, total * (0.35 + 0.65 * clamp((ilum - 0.4) / 0.55)))
    luz = por_tramos(hsol, [(-12, 0.0), (-6, 0.8), (-3, 1.0), (1, 1.0), (4, 0.6), (10, 0.2)])
    total = a.paso(
        f"Sol a {hsol:.0f}° en ese momento: "
        + (
            "luz de crepúsculo equilibrada"
            if luz > 0.9
            else "aún hay mucha luz"
            if hsol > 1
            else "ya es de noche: paisaje oscuro"
        ),
        total,
        total * (0.3 + 0.7 * luz),
    )
    if evento.get("horizonte", 0) > 4:
        total = a.paso(
            f"Relieve de {evento['horizonte']:.0f}°: asoma ya alta, sin el efecto de luna grande en el horizonte",
            total,
            total * (1 - 0.3 * clamp((evento["horizonte"] - 4) / 8)),
        )
    if camino:
        t_bajas = 1.0
        for p in camino:
            t_bajas *= 1 - PESO_CAMINO.get(int(p["km"]), 0.4) * valor(p, "low") / 100
        if t_bajas < 0.97:
            total = a.paso(
                f"Nubes bajas hacia la luna (hasta {max(valor(p, 'low') for p in camino):.0f} %)",
                total,
                total * t_bajas,
            )
    if local:
        nubes = valor(local, "cloud_cover", 0)
        if nubes > 20:
            total = a.paso(f"Nubosidad en el spot {nubes:.0f} %", total, total * (1 - 0.8 * clamp((nubes - 20) / 80)))
        P = valor(local, "precipitation_probability")
        if P > 20:
            total = a.paso(f"Lluvia {P:.0f} %", total, total * (1 - 0.6 * P / 100))
    return n
