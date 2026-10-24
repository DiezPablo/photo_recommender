"""Amanecer y atardecer: modelo del camino de la luz (lienzo de nubes, camino del sol, aire, relieve)."""

from __future__ import annotations

from .base import Acumulador, Nota, clamp, por_tramos, valor

# ===================================================== amanecer / atardecer ====
# Peso de las nubes bajas en cada punto del camino del sol (km → peso). Un banco de nubes bajas a
# 30-50 km basta para que el sol no ilumine el cielo (Stephen Bay, Sunsethue).
PESO_CAMINO = {15: 0.55, 40: 0.75, 80: 0.55, 150: 0.3}


KM_CAMINO = tuple(PESO_CAMINO)


PESO_MEDIAS = 0.5  # validado: en ERA5 las medias suelen ser altostratos grises (rasante.validacion, oct-2026)


def lienzo(alta: float, media: float, peso_medias: float | None = None) -> float:
    """Fracción (0-1) del cielo con nubes que pueden encenderse: altas y medias, sin contar dos veces."""
    w = PESO_MEDIAS if peso_medias is None else peso_medias
    return 1 - (1 - alta / 100) * (1 - w * media / 100)


def calidad_lienzo(c: float) -> float:
    """0-1. Ideal 40-70 % (consenso de guías y foros: 30-75 %). Una capa media/alta completa aún
    puede "bañar de rojo" el cielo si la luz pasa por debajo (NOAA), por eso no cae a cero."""
    return por_tramos(c, [(0.0, 0.0), (0.1, 0.15), (0.25, 0.6), (0.4, 0.95), (0.7, 1.0), (0.9, 0.8), (1.0, 0.6)])


def transmision_camino(camino: list[dict]) -> tuple[float, float, str]:
    """(transmisión para nubes medias, transmisión para nubes altas, texto del peor tramo).

    camino: [{"km": 15, "low": %, "mid": %, "high": %}, ...] hacia el sol."""
    t_media, t_alta, peor, peor_km = 1.0, 1.0, 0.0, None
    for p in camino:
        w = PESO_CAMINO.get(int(p["km"]), 0.4)
        bajas = valor(p, "low")
        f = 1 - w * bajas / 100
        t_media *= f
        t_alta *= f
        if p["km"] >= 80:  # una capa media espesa a lo lejos también deja sin luz a las altas
            t_alta *= 1 - 0.3 * clamp((valor(p, "mid") - 50) / 50)
        if bajas * w > peor:
            peor, peor_km = bajas * w, p["km"]
    texto = (
        (f"nubes bajas hacia el sol (hasta {max(valor(p, 'low') for p in camino):.0f} %, sobre todo a {peor_km} km)")
        if peor_km
        else "camino del sol despejado"
    )
    return t_media, t_alta, texto


def claridad_aire(
    aod: float | None, polvo: float | None, humedad: float, lluvia_previa_mm: float, prob_lluvia: float
) -> tuple[float, list[str]]:
    """Multiplicador del color por la limpieza del aire (0,25-1,12) y motivos."""
    k, motivos = 1.0, []
    if aod is not None:
        f = por_tramos(aod, [(0.0, 1.08), (0.1, 1.05), (0.2, 1.0), (0.4, 0.85), (0.8, 0.6)])
        if f > 1.02:
            motivos.append(f"aire muy limpio (AOD {aod:.2f})")
        elif f < 0.98:
            motivos.append(f"calima o aerosoles (AOD {aod:.2f})")
        k *= f
    if polvo is not None and polvo > 30:
        # La calima fuerte (15-mar-2022: 150+ µg/m³) deja un cielo pardo con el sol apenas visible
        k *= por_tramos(polvo, [(30, 0.95), (80, 0.7), (150, 0.35), (250, 0.25)])
        motivos.append(f"calima: polvo en suspensión ({polvo:.0f} µg/m³)")
    if humedad > 85:
        k *= 1 - 0.15 * clamp((humedad - 85) / 15)
        motivos.append(f"humedad {humedad:.0f} %")
    if lluvia_previa_mm >= 1 and prob_lluvia < 30:
        k *= 1.08
        motivos.append(f"aire lavado por la lluvia ({lluvia_previa_mm:.0f} mm en las 24 h previas)")
    return clamp(k, 0.25, 1.12), motivos


def nota_luz(
    local,
    camino: list[dict],
    aire: dict | None = None,
    es_agua: bool = False,
    momento: str = "atardecer",
    peso_medias: float | None = None,
    relieve: float | None = None,
    hora_relieve: str | None = None,
) -> Nota:
    """Amanecer o atardecer con el modelo de camino de la luz.

    local: condiciones en el spot en el pico de color (variables de Open-Meteo, interpoladas).
    camino: nubes en puntos a 15/40/80/150 km hacia el sol, en el mismo instante.
    aire: {"aod", "polvo", "lluvia_previa_mm"} (opcional).
    """
    aire = aire or {}
    L, M, H = valor(local, "cloud_cover_low"), valor(local, "cloud_cover_mid"), valor(local, "cloud_cover_high")
    P = valor(local, "precipitation_probability")
    lluvia = valor(local, "precipitation")
    V = valor(local, "visibility", 24000)
    viento = valor(local, "wind_speed_10m", 99)
    hum = valor(local, "relative_humidity_2m", 60)

    # Lienzo: 60 % el cielo sobre el spot, 40 % las nubes a 15-40 km hacia el sol (las que más se encienden)
    cerca = [p for p in camino if p["km"] <= 40] or [{"high": H, "mid": M}]
    c_sol = sum(lienzo(valor(p, "high"), valor(p, "mid"), peso_medias) for p in cerca) / len(cerca)
    c = 0.6 * lienzo(H, M, peso_medias) + 0.4 * c_sol
    q = calidad_lienzo(c)
    t_media, t_alta, texto_camino = transmision_camino(camino) if camino else (1.0, 1.0, "")
    # si el lienzo es sobre todo de nubes altas, cuenta su transmisión (la luz les llega desde más lejos)
    parte_alta = H / (H + 0.85 * M) if H + M > 0 else 0.5
    T = t_media * (1 - parte_alta) + t_alta * parte_alta
    k, motivos_aire = claridad_aire(aire.get("aod"), aire.get("polvo"), hum, aire.get("lluvia_previa_mm", 0.0), P)

    n = Nota(3.0, f"Base: luz rasante del sol al {momento}")
    a = Acumulador(n)
    luz = 3.0
    # 1) lienzo
    color = 7.0 * q
    if c < 0.1:
        n.suma(f"Cielo casi sin nubes altas ni medias ({c * 100:.0f} %): luz bonita, cielo plano", 0.0, minimo=0)
    else:
        texto = "Buen lienzo" if 0.35 <= c <= 0.8 else "Lienzo escaso" if c < 0.35 else "Cielo muy cubierto por arriba"
        n.suma(f"{texto} de nubes altas/medias ({c * 100:.0f} % sobre ti y hacia el sol)", color)
    # 2) camino de la luz
    total = a.paso(f"Camino del sol: {texto_camino}", luz + color, luz * t_media + color * T)
    luz, color = luz * t_media, color * T
    # 3) nubes bajas sobre el spot tapan el lienzo
    vis_cielo = 1 - 0.85 * (L / 100) ** 1.3
    total = a.paso(f"Nubes bajas sobre el spot ({L:.0f} %) tapan el cielo", total, luz + color * vis_cielo)
    color *= vis_cielo
    # 4) aire: afecta sobre todo al color; con calima o aerosoles densos vela también la luz directa
    if motivos_aire:
        k_luz = min(1.0, 0.3 + 0.7 * k) if k < 1 else 1.0
        total = a.paso("Aire: " + ", ".join(motivos_aire), total, luz * k_luz + color * k)
        luz, color = luz * k_luz, color * k
    # 5) lluvia y visibilidad
    m = (1 - 0.6 * P / 100) * (0.5 if lluvia >= 0.5 else 1.0)
    if m < 0.99:
        t = f"Lluvia: {P:.0f} % de probabilidad" + (f", {lluvia:.1f} mm previstos" if lluvia >= 0.5 else "")
        total = a.paso(t, total, total * m)
    if V < 5000:
        total = a.paso(f"Visibilidad {V / 1000:.1f} km: niebla o bruma en el spot", total, total * 0.6)
    # 6) relieve hacia el sol: una montaña delante quita la luz rasante y tapa el cielo bajo, donde
    #    está el color más intenso (rasante.terreno.horizonte, modelo digital de elevaciones)
    if relieve is not None and relieve > 1.0:
        f_luz = 1 - clamp((relieve - 1) / 6)
        f_color = 1 - 0.5 * clamp((relieve - 2) / 12)
        verbo = "asoma" if momento == "amanecer" else "se esconde"
        total = a.paso(
            f"Relieve hacia el sol a {relieve:.0f}°: {verbo} tras las montañas"
            + (f" a las {hora_relieve}" if hora_relieve else ""),
            total,
            luz * f_luz + color * f_color,
        )
        luz, color = luz * f_luz, color * f_color
    if es_agua and viento < 6:
        n.suma(f"Viento casi nulo ({viento:.0f} km/h): reflejos en el agua", 0.4)
        n.avisos.append("reflejos")
    n.extra = {"lienzo": round(c * 100), "transmision": round(T * 100), "claridad": round(k, 2)}
    if relieve is not None:
        n.extra["relieve"] = round(relieve, 1)
    return n
