"""
puntuacion.py — Notas 0-10 por tipo de salida, con desglose explicable.

Cada nota es una suma de aportaciones con nombre: se parte de una base y cada factor suma o
resta puntos. El desglose se publica tal cual en la web ("qué suma y qué resta"), así que
los textos están pensados para leerse.

Son heurísticas de partida, ajustables con la experiencia en el campo. Los tests de
tests/test_puntuacion.py fijan el sentido de cada factor con casos extremos.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _v(d, clave, defecto=0.0) -> float:
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


@dataclass
class Nota:
    base: float
    texto_base: str
    factores: list[tuple[str, float]] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def suma(self, texto: str, puntos: float, minimo: float = 0.05):
        if abs(puntos) >= minimo:
            self.factores.append((texto, round(puntos, 1)))

    @property
    def valor(self) -> float:
        return round(_clamp(self.base + sum(p for _, p in self.factores), 0, 10), 1)

    def a_dict(self) -> dict:
        return {"nota": self.valor,
                "desglose": [{"texto": self.texto_base, "puntos": round(self.base, 1)}]
                            + [{"texto": t, "puntos": p} for t, p in self.factores],
                "avisos": self.avisos}


# --------------------------------------------------- amanecer / atardecer ----
def nota_luz(local, horizonte, es_agua: bool = False, momento: str = "atardecer") -> Nota:
    """Amanecer o atardecer.

    local: condiciones en el spot a la hora del orto/ocaso (variables de Open-Meteo).
    horizonte: condiciones a ~40 km en la dirección del sol.

    Lo ideal es un "lienzo" de nubes altas o medias (30-70 %) que el sol ilumine desde abajo,
    con pocas nubes bajas en el spot y el horizonte hacia el sol despejado para que la luz pase.
    """
    L, M, H = _v(local, "cloud_cover_low"), _v(local, "cloud_cover_mid"), _v(local, "cloud_cover_high")
    Lh = _v(horizonte, "cloud_cover_low")
    Mh = _v(horizonte, "cloud_cover_mid")
    P = _v(local, "precipitation_probability")
    V = _v(local, "visibility", 24000)
    viento = _v(local, "wind_speed_10m", 99)

    n = Nota(4.0, "Base: luz de " + momento)
    lienzo = max(H, 0.8 * M)
    if lienzo < 15:
        n.suma(f"Cielo casi limpio (nubes altas/medias {lienzo:.0f} %): luz bonita pero cielo plano", -1.0)
    elif lienzo < 35:
        n.suma(f"Algunas nubes altas/medias ({lienzo:.0f} %) que pueden colorearse",
               1.0 + 2.0 * (lienzo - 15) / 20)
    elif lienzo <= 70:
        n.suma(f"Buen lienzo de nubes altas/medias ({lienzo:.0f} %)", 4.0)
    else:
        n.suma(f"Cielo muy cubierto por arriba ({lienzo:.0f} %): puede quedarse gris",
               4.0 - 6.0 * (lienzo - 70) / 30)

    if L > 30:
        n.suma(f"Nubes bajas en el spot ({L:.0f} %) tapan el cielo", -3.0 * _clamp((L - 30) / 60))
    if Lh > 30:
        n.suma(f"Banco de nubes bajas hacia el sol ({Lh:.0f} % a 40 km): la luz no llega a las nubes",
               -3.5 * _clamp((Lh - 30) / 60))
    elif lienzo >= 20 and Lh < 15 and Mh < 60:
        n.suma("Horizonte hacia el sol despejado: el sol iluminará las nubes por debajo", 1.0)
    if P >= 10:
        n.suma(f"Probabilidad de lluvia {P:.0f} %", -3.0 * P / 100)
    if V < 3000:
        n.suma(f"Visibilidad muy baja ({V / 1000:.1f} km): niebla o calima", -2.0)
    elif V < 10000:
        n.suma(f"Visibilidad reducida ({V / 1000:.0f} km)", -0.8)
    elif V >= 30000 and L < 30:
        n.suma(f"Aire muy limpio (visibilidad {V / 1000:.0f} km)", 0.3)
    if es_agua and viento < 6:
        n.suma(f"Viento casi nulo ({viento:.0f} km/h): reflejos en el agua", 0.5)
        n.avisos.append("reflejos")
    return n


# ------------------------------------------------- noche estrellada / VL ----
PENALIZACION_ZONA = {"0": 0.0, "1": 0.0, "2": 0.0, "3": -0.6, "4": -1.6, "5": -3.0, "6": -4.5, "7": -6.0}


def nota_astro(nubes: float, humedad: float, viento: float, rocio_margen: float,
               horas_sin_luna: float, horas_noche: float, luna_iluminacion: float,
               zona_lp: str | None, vl_horas_sin_luna: float = 0.0) -> Nota:
    """Noche estrellada / Vía Láctea.

    nubes, humedad, viento: medias en las horas oscuras útiles (sin luna si las hay).
    rocio_margen: mínimo de temperatura - punto de rocío en esas horas (°C).
    horas_sin_luna: horas de noche astronómica con la luna bajo el horizonte.
    zona_lp: zona del atlas de contaminación lumínica ("2b", "4a"...).
    """
    n = Nota(10.0, "Base: noche despejada, oscura y sin luna")
    if horas_noche <= 0:
        n.base = 0.0
        n.texto_base = "Sin noche astronómica"
        return n
    n.suma(f"Nubosidad media {nubes:.0f} %", -9.0 * (nubes / 100) ** 0.8)
    # La luna solo molesta si no deja ningún rato oscuro: con 3 h sin luna ya hay sesión
    oscuridad = _clamp(horas_sin_luna / 3)
    penal_luna = 5.0 * luna_iluminacion * (1 - oscuridad)
    if horas_sin_luna >= 0.5 and luna_iluminacion > 0.05:
        n.suma(f"Luna al {luna_iluminacion * 100:.0f} %, pero {horas_sin_luna:.1f} h de noche sin luna",
               -penal_luna)
    elif luna_iluminacion > 0.05:
        n.suma(f"Luna al {luna_iluminacion * 100:.0f} % sobre el horizonte toda la noche", -penal_luna - 0.5)
    if zona_lp:
        p = PENALIZACION_ZONA.get(zona_lp[0], 0.0) - (0.3 if zona_lp.endswith("b") and zona_lp[0] >= "3" else 0)
        if p:
            n.suma(f"Contaminación lumínica (zona {zona_lp} del atlas)", p)
    if humedad > 90:
        n.suma(f"Humedad muy alta ({humedad:.0f} %): calima y cielo lechoso", -0.8)
    if viento > 30:
        n.suma(f"Viento fuerte ({viento:.0f} km/h): trípode inestable", -0.8)
    elif viento > 20:
        n.suma(f"Viento moderado ({viento:.0f} km/h)", -0.3)
    if rocio_margen < 2:
        n.avisos.append("rocio")
    if vl_horas_sin_luna >= 1 and nubes < 50:
        n.suma(f"Núcleo de la Vía Láctea fotografiable {vl_horas_sin_luna:.1f} h", 0.5)
    return n


# --------------------------------------------------------- niebla / mar ----
def nota_niebla(madrugada: list[dict], elevacion_spot: float | None = None,
                bajas_alrededor: float | None = None) -> Nota:
    """Niebla al amanecer (en el spot) o mar de nubes (spot alto sobre nubes bajas del entorno).

    madrugada: filas horarias (dict) desde 3 h antes hasta 1 h después del amanecer.
    bajas_alrededor: nubes bajas medias en los puntos de horizonte (más bajos que el spot).
    """
    n = Nota(0.0, "Base: sin niebla")
    if not madrugada:
        return n
    # la hora más favorable de la madrugada
    def favorable(f):
        rh, t, td = _v(f, "relative_humidity_2m"), _v(f, "temperature_2m"), _v(f, "dew_point_2m")
        v = _v(f, "wind_speed_10m", 30)
        return _clamp((rh - 85) / 12) * _clamp((3 - (t - td)) / 3) * _clamp((15 - v) / 12)
    f = max(madrugada, key=favorable)
    rh, t, td = _v(f, "relative_humidity_2m"), _v(f, "temperature_2m"), _v(f, "dew_point_2m")
    v, vis = _v(f, "wind_speed_10m", 30), _v(f, "visibility", 24000)
    bajas = _v(f, "cloud_cover_low")
    P = max(_v(x, "precipitation_probability") for x in madrugada)

    puntos_h = 4.0 * _clamp((rh - 85) / 12)
    puntos_td = 3.0 * _clamp((3 - (t - td)) / 3)
    puntos_v = 2.0 * _clamp((15 - v) / 12)
    # sin humedad suficiente lo demás no basta: el aire seco no condensa
    if puntos_h > 0:
        n.suma(f"Humedad {rh:.0f} %", puntos_h)
        n.suma(f"Temperatura casi en el punto de rocío ({t - td:.1f} °C de margen)", puntos_td)
        n.suma(f"Viento flojo ({v:.0f} km/h)", puntos_v)
        if vis < 1000:
            n.suma(f"El modelo ya prevé visibilidad de {vis / 1000:.1f} km", 1.0)
    else:
        n.suma(f"Aire demasiado seco para niebla ({rh:.0f} %)", 0.0, minimo=0)
    if P >= 50:
        n.suma(f"Lluvia probable ({P:.0f} %): más bruma que niebla fotogénica", -2.0)
    # Mar de nubes: spot alto y despejado con nubes bajas por debajo
    if (elevacion_spot or 0) >= 1000 and bajas_alrededor is not None:
        if bajas_alrededor >= 60 and bajas < 40 and rh < 95:
            n.suma(f"Posible mar de nubes: el spot está a {elevacion_spot:.0f} m y hay nubes bajas "
                   f"alrededor ({bajas_alrededor:.0f} %)", 5.0)
            n.avisos.append("mar_de_nubes")
    return n
