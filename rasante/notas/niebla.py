"""Niebla de radiación (calibrada con METAR) y mar de nubes (perfil vertical)."""

from __future__ import annotations

from .base import Nota, clamp, por_tramos, valor

# ========================================================= niebla / mar ====
TIPOS_VISTA = {"mirador", "cumbre", "acantilado", "cabo", "faro"}


TIPOS_NIEBLA = {"embalse", "lago", "río", "puente", "cascada", "paraje"}


# Calibración del índice de niebla con 11 792 madrugadas de METAR (Barajas, Getafe, Cuatro Vientos y
# Torrejón, 2016-2025) y ERA5: índice → frecuencia real de niebla (FG o visibilidad < 1 km).
CALIBRACION_NIEBLA = [
    (0.0, 0.003),
    (0.3, 0.016),
    (0.5, 0.04),
    (0.68, 0.077),
    (0.8, 0.17),
    (0.89, 0.25),
    (0.97, 0.46),
    (1.0, 0.5),
]


def prob_niebla_radiacion(madrugada: list[dict]) -> tuple[float, dict]:
    """Probabilidad (0-1) de niebla al amanecer en el spot.

    Ajustada con observaciones reales (rasante.validacion): lo que separa las madrugadas con niebla es la
    **humedad máxima** (rampa del 85 al 100 %) y el **viento mínimo** (la niebla aguanta hasta ~6 km/h
    y desaparece hacia 20 km/h). La nubosidad de la noche y la lluvia previa, ingredientes clásicos,
    no aportaron nada una vez conocida la humedad (que ya recoge su efecto), así que no se usan.
    Si el modelo prevé visibilidad < 1 km con el aire casi saturado (≥ 90 %), es evidencia directa; con el
    aire seco no (en cumbres y lagos de montaña la visibilidad del modelo baja sin niebla: en los Lagos de
    Cabdella daba 0,3 km con un 71 % de humedad). Esta regla no está en la calibración con METAR."""
    if not madrugada:
        return 0.0, {}
    hr = max(valor(f, "relative_humidity_2m") for f in madrugada)
    viento = min(valor(f, "wind_speed_10m", 30) for f in madrugada)
    vis = min(valor(f, "visibility", 24000) for f in madrugada)
    indice = clamp((hr - 85) / 15) * clamp((20 - viento) / 14)
    p = por_tramos(indice, CALIBRACION_NIEBLA)
    if vis < 1000 and hr >= 90:
        p = max(p, 0.6)
    return p, {"humedad": hr, "viento": viento, "visibilidad": vis, "indice": indice}


def capa_nubosa(perfil: dict) -> dict | None:
    """Techo de la capa de nubes bajas/niebla a partir del perfil por niveles de presión de un punto
    del llano: {"niveles": [{"hpa", "z" (m), "t" (°C), "hr" (%), "nubes" (%)}, ...] de abajo arriba}.
    Devuelve {"techo": m, "cobertura": %, "inversion": °C} o None si no hay capa baja."""
    niveles = [x for x in perfil.get("niveles", []) if x.get("z") is not None]
    if not niveles:
        return None
    capa = []
    for x in niveles:
        if (x.get("nubes") or 0) >= 40 or (x.get("hr") or 0) >= 96:
            capa.append(x)
        elif capa or x["z"] > 1200:
            break
    if not capa:
        return None
    techo = capa[-1]
    siguiente = next((x for x in niveles if x["z"] > techo["z"]), None)
    techo_m = techo["z"] + (0.5 * (siguiente["z"] - techo["z"]) if siguiente else 100)
    inversion = (siguiente["t"] - techo["t"]) if siguiente and siguiente.get("t") is not None else 0.0
    return {"techo": techo_m, "cobertura": max(x.get("nubes") or 0 for x in capa), "inversion": inversion}


def nota_niebla(
    madrugada: list[dict],
    elevacion_spot: float | None = None,
    capa: dict | None = None,
    tipo: str | None = None,
    bajas_spot: float | None = None,
) -> Nota:
    """Niebla y mar de nubes al amanecer: dos escenarios y se queda el mejor.

    - Niebla en el spot (radiación): fotogénica en embalses, ríos, bosques; en miradores y cumbres
      significa estar dentro de la nube y no ver nada.
    - Mar de nubes: el spot queda por encima del techo de la capa de nubes bajas/niebla del llano
      (perfil vertical del modelo), con inversión encima que la deja plana.
    """
    if not madrugada:
        return Nota(0.0, "Base: sin datos de madrugada")
    p, det = prob_niebla_radiacion(madrugada)
    lluvia = max(valor(x, "precipitation_probability") for x in madrugada)
    vista = (tipo or "") in TIPOS_VISTA

    a = Nota(0.0, "Base: sin niebla")
    if p >= 0.02:
        # ~50 % de probabilidad real ya es una apuesta excelente: la niebla nunca es segura
        a.suma(
            f"Niebla probable en el spot: {p * 100:.0f} % (humedad máx. {det['humedad']:.0f} %, "
            f"viento mín. {det['viento']:.0f} km/h)",
            9.0 * min(1.0, p / 0.5),
        )
        if det["visibilidad"] < 1000:
            a.suma(f"El modelo prevé visibilidad de {det['visibilidad'] / 1000:.1f} km", 1.0)
        if vista:
            a.suma(f"En un {tipo} la niebla tapa la vista: estarás dentro de la nube", -0.65 * a.bruta)
        elif (tipo or "") in TIPOS_NIEBLA:
            a.suma(f"Niebla sobre {tipo}: muy fotogénica", 0.08 * a.bruta)
        if lluvia >= 50:
            a.suma(f"Lluvia probable ({lluvia:.0f} %): más bruma que niebla fotogénica", -0.3 * a.bruta)
    else:
        a.suma(f"Aire seco o con viento: niebla improbable ({p * 100:.1f} %)", 0.0, minimo=0)
    a.extra = {"probabilidad": round(p * 100)}

    b = None
    if capa and elevacion_spot is not None:
        margen = elevacion_spot - capa["techo"]
        dentro = (bajas_spot or 0) >= 60 or p >= 0.35
        if margen >= 60 and not dentro and capa["cobertura"] >= 50:
            b = Nota(4.0, f"Base: spot por encima del techo de las nubes bajas ({capa['techo']:.0f} m)")
            b.suma(
                f"Capa nubosa en valles y llano: {capa['cobertura']:.0f} %", 3.5 * clamp((capa["cobertura"] - 50) / 45)
            )
            if capa["inversion"] >= 1:
                b.suma(
                    f"Inversión térmica de {capa['inversion']:.0f} °C encima: mar plano y estable",
                    min(1.5, 0.5 * capa["inversion"]),
                )
            if 100 <= margen <= 900:
                b.suma(f"Estás {margen:.0f} m por encima: perspectiva ideal sobre el mar", 1.0)
            elif margen > 900:
                b.suma(f"Estás {margen:.0f} m por encima: el mar queda lejos", 0.3)
            if lluvia >= 50:
                b.suma(f"Lluvia probable ({lluvia:.0f} %)", -2.0)
            b.avisos.append("mar_de_nubes")
            b.extra = {"techo": round(capa["techo"]), "margen": round(margen)}
        elif -150 < margen < 60 and capa["cobertura"] >= 50:
            a.avisos.append("techo_nubes_cerca")
    return b if b is not None and b.valor >= a.valor else a
