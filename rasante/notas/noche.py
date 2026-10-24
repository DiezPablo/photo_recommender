"""Noche estrellada y Vía Láctea: mejor ventana de 3 h, transparencia y contaminación lumínica."""

from __future__ import annotations

from .base import Acumulador, Nota, clamp, por_tramos, valor


# ==================================================== noche / Vía Láctea ====
def factor_sqm(sqm: float | None) -> float:
    """Contaminación lumínica local (brillo en el cénit, mag/arcsec²) → multiplicador."""
    if sqm is None:
        return 0.85
    # Calibrado para el fotógrafo de Madrid: un cielo Bortle 4-5 despejado y sin luna sí merece la
    # salida (la Vía Láctea se ve y se fotografía), uno urbano no.
    return por_tramos(
        sqm,
        [(17.5, 0.15), (18.5, 0.3), (19.5, 0.5), (20.25, 0.68), (20.7, 0.8), (21.1, 0.88), (21.4, 0.94), (21.6, 1.0)],
    )


def factor_transparencia(
    vapor_mm: float | None, aod: float | None, humedad: float, elevacion: float | None
) -> tuple[float, list[str]]:
    """Transparencia: vapor de agua en la columna, aerosoles y humedad en superficie."""
    k, motivos = 1.0, []
    if vapor_mm is not None:
        f = por_tramos(vapor_mm, [(6, 1.0), (12, 0.95), (20, 0.86), (30, 0.75), (40, 0.68)])
        if f < 0.97:
            motivos.append(f"vapor de agua {vapor_mm:.0f} mm")
        k *= f
    if aod is not None:
        f = por_tramos(aod, [(0.05, 1.0), (0.1, 0.97), (0.2, 0.88), (0.4, 0.7), (0.8, 0.5)])
        if f < 0.97:
            motivos.append(f"aerosoles/calima (AOD {aod:.2f})")
        k *= f
    if humedad > 85:
        k *= 1 - 0.2 * clamp((humedad - 85) / 15)
        motivos.append(f"humedad {humedad:.0f} %")
    if elevacion and elevacion > 1400:
        k *= 1.04  # por encima de buena parte de la bruma
    return clamp(k, 0.4, 1.04), motivos


def nota_astro(
    horas: list[dict],
    sqm: float | None,
    zona_lp: str | None = None,
    cupula: dict | None = None,
    vapor_mm: float | None = None,
    aod: float | None = None,
    elevacion: float | None = None,
    vl_horas_sin_luna: float = 0.0,
    vl_altura_max: float | None = None,
    margen_rocio: float = 99.0,
    rachas: float = 0.0,
    humedad: float = 60.0,
) -> Nota:
    """Noche estrellada / Vía Láctea.

    horas: una entrada por hora de noche astronómica: {"t": "HH:MM", "nubes": %,
           "luna": 0-1 (luz de luna: iluminación si está sobre el horizonte, 0 si no)}.
    cupula: {"zona": zona más brillante hacia donde se mira, "km": distancia, "hacia": texto}.
    """
    n = Nota(10.0, "Base: noche oscura, despejada y transparente")
    if not horas:
        n.base, n.texto_base = 0.0, "Sin noche astronómica"
        return n
    a = Acumulador(n)

    cal = [((1 - valor(h, "nubes") / 100) ** 1.5, 1 - 0.75 * clamp(valor(h, "luna"))) for h in horas]
    q = [c * o for c, o in cal]
    ventana = min(3, len(q))
    i = max(range(len(q) - ventana + 1), key=lambda j: sum(q[j : j + ventana]))
    tramo = horas[i : i + ventana]
    cielo = sum(c for c, _ in cal[i : i + ventana]) / ventana
    oscuridad = sum(o for _, o in cal[i : i + ventana]) / ventana
    fin = horas[i + ventana]["t"] if i + ventana < len(horas) else "fin de la noche"
    n.extra = {"ventana": [tramo[0]["t"], fin], "horas_buenas": sum(1 for x in q if x >= 0.6)}

    nubes_media = sum(valor(h, "nubes") for h in tramo) / ventana
    total = a.paso(f"Nubes en la mejor ventana ({tramo[0]['t']}–{fin}): {nubes_media:.0f} %", 10.0, 10.0 * cielo)
    if oscuridad < 0.99:
        total = a.paso("Luz de la luna en esa ventana", total, total * oscuridad)
    k, motivos = factor_transparencia(vapor_mm, aod, humedad, elevacion)
    if abs(k - 1) > 0.01:
        total = a.paso(
            "Transparencia: " + (", ".join(motivos) if motivos else "spot alto, sobre la bruma"), total, total * k
        )
    f = factor_sqm(sqm)
    if f < 0.99:
        total = a.paso(f"Contaminación lumínica local (zona {zona_lp or '?'}, {sqm or 0:.2f} mag/″²)", total, total * f)
    if cupula and cupula.get("zona"):
        z = cupula["zona"]
        penal = {"5": 0.93, "6": 0.85, "7": 0.75}.get(z[0], 1.0)
        if penal < 1:
            total = a.paso(
                f"Cúpula de luz hacia {cupula.get('hacia', 'el sur')} (zona {z} a {cupula['km']} km)",
                total,
                total * penal,
            )
    if rachas > 30:
        total = a.paso(
            f"Rachas de {rachas:.0f} km/h: trípode inestable",
            total,
            total * por_tramos(rachas, [(30, 0.95), (50, 0.8), (70, 0.65), (90, 0.5)]),
        )
    if vl_horas_sin_luna >= 1 and cielo > 0.5:
        bonus = 0.5 + 0.5 * clamp(((vl_altura_max or 10) - 10) / 15)
        n.suma(
            f"Núcleo de la Vía Láctea fotografiable {vl_horas_sin_luna:.1f} h (hasta {vl_altura_max or 0:.0f}°)", bonus
        )
    if margen_rocio < 2:
        n.avisos.append("rocio")
    return n
