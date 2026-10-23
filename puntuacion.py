"""
puntuacion.py — Modelos de predicción: nota 0-10 por tipo de salida, con desglose explicable.

Versión 2 (oct-2026), basada en lo que miden los servicios especializados y lo que repiten los
fotógrafos (fuentes en registro.md):

- Amanecer/atardecer: modelo de **camino de la luz** (como Sunsethue): para que las nubes se
  enciendan hace falta (1) un lienzo de nubes medias/altas sobre el observador y hacia el sol,
  (2) que la luz del sol llegue a ellas: sin nubes bajas a lo largo de su camino (15-150 km hacia
  el sol), (3) que las nubes bajas locales no tapen el lienzo y (4) aire limpio (aerosoles, polvo
  y humedad apagan el color; tras la lluvia el aire está lavado). Se evalúa en el pico de color:
  15 min antes de salir el sol / 15 min después de ponerse.
- Noche: calidad hora a hora (oscuridad × cielo despejado) y se queda la **mejor ventana de 3 h**,
  multiplicada por la transparencia (vapor de agua, aerosoles, humedad) y la contaminación lumínica
  local y la **cúpula de luz hacia donde se mira** (núcleo de la Vía Láctea o el sur).
- Niebla: probabilidad calibrada con 10 años de METAR de los aeropuertos de Madrid (humedad máxima
  y viento mínimo de madrugada) y **mar de nubes** con el perfil vertical real (techo de la capa
  nubosa en el llano y altura del spot).

Las notas son sumas de factores con nombre: cada factor muestra cuánto cambia la nota, de modo que
el desglose de la web suma exactamente la nota (antes del recorte a 0-10).
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


def _tramos(x: float, puntos: list[tuple[float, float]]) -> float:
    """Interpolación lineal por tramos: puntos (x, y) ordenados por x."""
    if x <= puntos[0][0]:
        return puntos[0][1]
    for (x0, y0), (x1, y1) in zip(puntos, puntos[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return puntos[-1][1]


@dataclass
class Nota:
    base: float
    texto_base: str
    factores: list[tuple[str, float]] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)   # datos del modelo útiles para la web

    def suma(self, texto: str, puntos: float, minimo: float = 0.05):
        if abs(puntos) >= minimo:
            self.factores.append((texto, round(puntos, 1)))

    @property
    def bruta(self) -> float:
        return self.base + sum(p for _, p in self.factores)

    @property
    def valor(self) -> float:
        return round(_clamp(self.bruta, 0, 10), 1)

    def a_dict(self) -> dict:
        d = {"nota": self.valor,
             "desglose": [{"texto": self.texto_base, "puntos": round(self.base, 1)}]
                         + [{"texto": t, "puntos": p} for t, p in self.factores],
             "avisos": self.avisos}
        if self.extra:
            d["modelo"] = self.extra
        return d


class _Acumulador:
    """Explica como sumas una nota que se calcula multiplicando: cada paso anota cuánto cambia."""

    def __init__(self, nota: Nota):
        self.n = nota

    def paso(self, texto: str, antes: float, despues: float, minimo: float = 0.05) -> float:
        self.n.suma(texto, despues - antes, minimo)
        return despues


# ===================================================== amanecer / atardecer ====
# Peso de las nubes bajas en cada punto del camino del sol (km → peso). Un banco de nubes bajas a
# 30-50 km basta para que el sol no ilumine el cielo (Stephen Bay, Sunsethue).
PESO_CAMINO = {15: 0.55, 40: 0.75, 80: 0.55, 150: 0.3}
KM_CAMINO = tuple(PESO_CAMINO)


PESO_MEDIAS = 0.5    # validado: en ERA5 las medias suelen ser altostratos grises (validar.py, oct-2026)


def lienzo(alta: float, media: float, peso_medias: float | None = None) -> float:
    """Fracción (0-1) del cielo con nubes que pueden encenderse: altas y medias, sin contar dos veces."""
    w = PESO_MEDIAS if peso_medias is None else peso_medias
    return 1 - (1 - alta / 100) * (1 - w * media / 100)


def calidad_lienzo(c: float) -> float:
    """0-1. Ideal 40-70 % (consenso de guías y foros: 30-75 %). Una capa media/alta completa aún
    puede "bañar de rojo" el cielo si la luz pasa por debajo (NOAA), por eso no cae a cero."""
    return _tramos(c, [(0.0, 0.0), (0.1, 0.15), (0.25, 0.6), (0.4, 0.95), (0.7, 1.0), (0.9, 0.8), (1.0, 0.6)])


def transmision_camino(camino: list[dict]) -> tuple[float, float, str]:
    """(transmisión para nubes medias, transmisión para nubes altas, texto del peor tramo).

    camino: [{"km": 15, "low": %, "mid": %, "high": %}, ...] hacia el sol."""
    t_media, t_alta, peor, peor_km = 1.0, 1.0, 0.0, None
    for p in camino:
        w = PESO_CAMINO.get(int(p["km"]), 0.4)
        bajas = _v(p, "low")
        f = 1 - w * bajas / 100
        t_media *= f
        t_alta *= f
        if p["km"] >= 80:   # una capa media espesa a lo lejos también deja sin luz a las altas
            t_alta *= 1 - 0.3 * _clamp((_v(p, "mid") - 50) / 50)
        if bajas * w > peor:
            peor, peor_km = bajas * w, p["km"]
    texto = (f"nubes bajas hacia el sol (hasta {max(_v(p, 'low') for p in camino):.0f} %, sobre todo a "
             f"{peor_km} km)") if peor_km else "camino del sol despejado"
    return t_media, t_alta, texto


def claridad_aire(aod: float | None, polvo: float | None, humedad: float, lluvia_previa_mm: float,
                  prob_lluvia: float) -> tuple[float, list[str]]:
    """Multiplicador del color por la limpieza del aire (0,25-1,12) y motivos."""
    k, motivos = 1.0, []
    if aod is not None:
        f = _tramos(aod, [(0.0, 1.08), (0.1, 1.05), (0.2, 1.0), (0.4, 0.85), (0.8, 0.6)])
        if f > 1.02:
            motivos.append(f"aire muy limpio (AOD {aod:.2f})")
        elif f < 0.98:
            motivos.append(f"calima o aerosoles (AOD {aod:.2f})")
        k *= f
    if polvo is not None and polvo > 30:
        # La calima fuerte (15-mar-2022: 150+ µg/m³) deja un cielo pardo con el sol apenas visible
        k *= _tramos(polvo, [(30, 0.95), (80, 0.7), (150, 0.35), (250, 0.25)])
        motivos.append(f"calima: polvo en suspensión ({polvo:.0f} µg/m³)")
    if humedad > 85:
        k *= 1 - 0.15 * _clamp((humedad - 85) / 15)
        motivos.append(f"humedad {humedad:.0f} %")
    if lluvia_previa_mm >= 1 and prob_lluvia < 30:
        k *= 1.08
        motivos.append(f"aire lavado por la lluvia ({lluvia_previa_mm:.0f} mm en las 24 h previas)")
    return _clamp(k, 0.25, 1.12), motivos


def nota_luz(local, camino: list[dict], aire: dict | None = None, es_agua: bool = False,
             momento: str = "atardecer", peso_medias: float | None = None,
             relieve: float | None = None, hora_relieve: str | None = None) -> Nota:
    """Amanecer o atardecer con el modelo de camino de la luz.

    local: condiciones en el spot en el pico de color (variables de Open-Meteo, interpoladas).
    camino: nubes en puntos a 15/40/80/150 km hacia el sol, en el mismo instante.
    aire: {"aod", "polvo", "lluvia_previa_mm"} (opcional).
    """
    aire = aire or {}
    L, M, H = _v(local, "cloud_cover_low"), _v(local, "cloud_cover_mid"), _v(local, "cloud_cover_high")
    P = _v(local, "precipitation_probability")
    lluvia = _v(local, "precipitation")
    V = _v(local, "visibility", 24000)
    viento = _v(local, "wind_speed_10m", 99)
    hum = _v(local, "relative_humidity_2m", 60)

    # Lienzo: 60 % el cielo sobre el spot, 40 % las nubes a 15-40 km hacia el sol (las que más se encienden)
    cerca = [p for p in camino if p["km"] <= 40] or [{"high": H, "mid": M}]
    c_sol = sum(lienzo(_v(p, "high"), _v(p, "mid"), peso_medias) for p in cerca) / len(cerca)
    c = 0.6 * lienzo(H, M, peso_medias) + 0.4 * c_sol
    q = calidad_lienzo(c)
    t_media, t_alta, texto_camino = transmision_camino(camino) if camino else (1.0, 1.0, "")
    # si el lienzo es sobre todo de nubes altas, cuenta su transmisión (la luz les llega desde más lejos)
    parte_alta = H / (H + 0.85 * M) if H + M > 0 else 0.5
    T = t_media * (1 - parte_alta) + t_alta * parte_alta
    k, motivos_aire = claridad_aire(aire.get("aod"), aire.get("polvo"), hum,
                                    aire.get("lluvia_previa_mm", 0.0), P)

    n = Nota(3.0, f"Base: luz rasante del sol al {momento}")
    a = _Acumulador(n)
    luz = 3.0
    # 1) lienzo
    color = 7.0 * q
    if c < 0.1:
        n.suma(f"Cielo casi sin nubes altas ni medias ({c * 100:.0f} %): luz bonita, cielo plano", 0.0, minimo=0)
    else:
        texto = ("Buen lienzo" if 0.35 <= c <= 0.8 else "Lienzo escaso" if c < 0.35
                 else "Cielo muy cubierto por arriba")
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
    #    está el color más intenso (horizonte.py, modelo digital de elevaciones)
    if relieve is not None and relieve > 1.0:
        f_luz = 1 - _clamp((relieve - 1) / 6)
        f_color = 1 - 0.5 * _clamp((relieve - 2) / 12)
        verbo = "asoma" if momento == "amanecer" else "se esconde"
        total = a.paso(f"Relieve hacia el sol a {relieve:.0f}°: {verbo} tras las montañas"
                       + (f" a las {hora_relieve}" if hora_relieve else ""), total, luz * f_luz + color * f_color)
        luz, color = luz * f_luz, color * f_color
    if es_agua and viento < 6:
        n.suma(f"Viento casi nulo ({viento:.0f} km/h): reflejos en el agua", 0.4)
        n.avisos.append("reflejos")
    n.extra = {"lienzo": round(c * 100), "transmision": round(T * 100), "claridad": round(k, 2)}
    if relieve is not None:
        n.extra["relieve"] = round(relieve, 1)
    return n


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
    n = Nota(10.0, f"{accion} la luna a las {evento['hora']} hacia {evento['azimut']:.0f}°: luna llena en el crepúsculo")
    a = _Acumulador(n)
    total = 10.0
    total = a.paso(f"Luna al {ilum * 100:.0f} %", total, total * (0.35 + 0.65 * _clamp((ilum - 0.4) / 0.55)))
    luz = _tramos(hsol, [(-12, 0.0), (-6, 0.8), (-3, 1.0), (1, 1.0), (4, 0.6), (10, 0.2)])
    total = a.paso(f"Sol a {hsol:.0f}° en ese momento: " + ("luz de crepúsculo equilibrada" if luz > 0.9
                   else "aún hay mucha luz" if hsol > 1 else "ya es de noche: paisaje oscuro"),
                   total, total * (0.3 + 0.7 * luz))
    if evento.get("horizonte", 0) > 4:
        total = a.paso(f"Relieve de {evento['horizonte']:.0f}°: asoma ya alta, sin el efecto de luna grande en el horizonte",
                       total, total * (1 - 0.3 * _clamp((evento["horizonte"] - 4) / 8)))
    if camino:
        t_bajas = 1.0
        for p in camino:
            t_bajas *= 1 - PESO_CAMINO.get(int(p["km"]), 0.4) * _v(p, "low") / 100
        if t_bajas < 0.97:
            total = a.paso(f"Nubes bajas hacia la luna (hasta {max(_v(p, 'low') for p in camino):.0f} %)",
                           total, total * t_bajas)
    if local:
        nubes = _v(local, "cloud_cover", 0)
        if nubes > 20:
            total = a.paso(f"Nubosidad en el spot {nubes:.0f} %", total, total * (1 - 0.8 * _clamp((nubes - 20) / 80)))
        P = _v(local, "precipitation_probability")
        if P > 20:
            total = a.paso(f"Lluvia {P:.0f} %", total, total * (1 - 0.6 * P / 100))
    return n


# ==================================================== noche / Vía Láctea ====
def factor_sqm(sqm: float | None) -> float:
    """Contaminación lumínica local (brillo en el cénit, mag/arcsec²) → multiplicador."""
    if sqm is None:
        return 0.85
    # Calibrado para el fotógrafo de Madrid: un cielo Bortle 4-5 despejado y sin luna sí merece la
    # salida (la Vía Láctea se ve y se fotografía), uno urbano no.
    return _tramos(sqm, [(17.5, 0.15), (18.5, 0.3), (19.5, 0.5), (20.25, 0.68), (20.7, 0.8),
                         (21.1, 0.88), (21.4, 0.94), (21.6, 1.0)])


def factor_transparencia(vapor_mm: float | None, aod: float | None, humedad: float,
                         elevacion: float | None) -> tuple[float, list[str]]:
    """Transparencia: vapor de agua en la columna, aerosoles y humedad en superficie."""
    k, motivos = 1.0, []
    if vapor_mm is not None:
        f = _tramos(vapor_mm, [(6, 1.0), (12, 0.95), (20, 0.86), (30, 0.75), (40, 0.68)])
        if f < 0.97:
            motivos.append(f"vapor de agua {vapor_mm:.0f} mm")
        k *= f
    if aod is not None:
        f = _tramos(aod, [(0.05, 1.0), (0.1, 0.97), (0.2, 0.88), (0.4, 0.7), (0.8, 0.5)])
        if f < 0.97:
            motivos.append(f"aerosoles/calima (AOD {aod:.2f})")
        k *= f
    if humedad > 85:
        k *= 1 - 0.2 * _clamp((humedad - 85) / 15)
        motivos.append(f"humedad {humedad:.0f} %")
    if elevacion and elevacion > 1400:
        k *= 1.04   # por encima de buena parte de la bruma
    return _clamp(k, 0.4, 1.04), motivos


def nota_astro(horas: list[dict], sqm: float | None, zona_lp: str | None = None,
               cupula: dict | None = None, vapor_mm: float | None = None, aod: float | None = None,
               elevacion: float | None = None, vl_horas_sin_luna: float = 0.0,
               vl_altura_max: float | None = None, margen_rocio: float = 99.0,
               rachas: float = 0.0, humedad: float = 60.0) -> Nota:
    """Noche estrellada / Vía Láctea.

    horas: una entrada por hora de noche astronómica: {"t": "HH:MM", "nubes": %,
           "luna": 0-1 (luz de luna: iluminación si está sobre el horizonte, 0 si no)}.
    cupula: {"zona": zona más brillante hacia donde se mira, "km": distancia, "hacia": texto}.
    """
    n = Nota(10.0, "Base: noche oscura, despejada y transparente")
    if not horas:
        n.base, n.texto_base = 0.0, "Sin noche astronómica"
        return n
    a = _Acumulador(n)

    cal = [((1 - _v(h, "nubes") / 100) ** 1.5, 1 - 0.75 * _clamp(_v(h, "luna"))) for h in horas]
    q = [c * o for c, o in cal]
    ventana = min(3, len(q))
    i = max(range(len(q) - ventana + 1), key=lambda j: sum(q[j:j + ventana]))
    tramo = horas[i:i + ventana]
    cielo = sum(c for c, _ in cal[i:i + ventana]) / ventana
    oscuridad = sum(o for _, o in cal[i:i + ventana]) / ventana
    fin = horas[i + ventana]["t"] if i + ventana < len(horas) else "fin de la noche"
    n.extra = {"ventana": [tramo[0]["t"], fin], "horas_buenas": sum(1 for x in q if x >= 0.6)}

    nubes_media = sum(_v(h, "nubes") for h in tramo) / ventana
    total = a.paso(f"Nubes en la mejor ventana ({tramo[0]['t']}–{fin}): {nubes_media:.0f} %", 10.0, 10.0 * cielo)
    if oscuridad < 0.99:
        total = a.paso("Luz de la luna en esa ventana", total, total * oscuridad)
    k, motivos = factor_transparencia(vapor_mm, aod, humedad, elevacion)
    if abs(k - 1) > 0.01:
        total = a.paso("Transparencia: " + (", ".join(motivos) if motivos else "spot alto, sobre la bruma"),
                       total, total * k)
    f = factor_sqm(sqm)
    if f < 0.99:
        total = a.paso(f"Contaminación lumínica local (zona {zona_lp or '?'}, {sqm or 0:.2f} mag/″²)",
                       total, total * f)
    if cupula and cupula.get("zona"):
        z = cupula["zona"]
        penal = {"5": 0.93, "6": 0.85, "7": 0.75}.get(z[0], 1.0)
        if penal < 1:
            total = a.paso(f"Cúpula de luz hacia {cupula.get('hacia', 'el sur')} (zona {z} a {cupula['km']} km)",
                           total, total * penal)
    if rachas > 30:
        total = a.paso(f"Rachas de {rachas:.0f} km/h: trípode inestable", total,
                       total * _tramos(rachas, [(30, 0.95), (50, 0.8), (70, 0.65), (90, 0.5)]))
    if vl_horas_sin_luna >= 1 and cielo > 0.5:
        bonus = 0.5 + 0.5 * _clamp(((vl_altura_max or 10) - 10) / 15)
        n.suma(f"Núcleo de la Vía Láctea fotografiable {vl_horas_sin_luna:.1f} h (hasta {vl_altura_max or 0:.0f}°)", bonus)
    if margen_rocio < 2:
        n.avisos.append("rocio")
    return n


# ========================================================= niebla / mar ====
TIPOS_VISTA = {"mirador", "cumbre", "acantilado", "cabo", "faro"}
TIPOS_NIEBLA = {"embalse", "lago", "río", "puente", "cascada", "paraje"}


# Calibración del índice de niebla con 11 792 madrugadas de METAR (Barajas, Getafe, Cuatro Vientos y
# Torrejón, 2016-2025) y ERA5: índice → frecuencia real de niebla (FG o visibilidad < 1 km).
CALIBRACION_NIEBLA = [(0.0, 0.003), (0.3, 0.016), (0.5, 0.04), (0.68, 0.077), (0.8, 0.17), (0.89, 0.25),
                      (0.97, 0.46), (1.0, 0.5)]


def prob_niebla_radiacion(madrugada: list[dict]) -> tuple[float, dict]:
    """Probabilidad (0-1) de niebla al amanecer en el spot.

    Ajustada con observaciones reales (validar.py): lo que separa las madrugadas con niebla es la
    **humedad máxima** (rampa del 85 al 100 %) y el **viento mínimo** (la niebla aguanta hasta ~6 km/h
    y desaparece hacia 20 km/h). La nubosidad de la noche y la lluvia previa, ingredientes clásicos,
    no aportaron nada una vez conocida la humedad (que ya recoge su efecto), así que no se usan.
    Si el modelo prevé visibilidad < 1 km, es evidencia directa."""
    if not madrugada:
        return 0.0, {}
    hr = max(_v(f, "relative_humidity_2m") for f in madrugada)
    viento = min(_v(f, "wind_speed_10m", 30) for f in madrugada)
    vis = min(_v(f, "visibility", 24000) for f in madrugada)
    indice = _clamp((hr - 85) / 15) * _clamp((20 - viento) / 14)
    p = _tramos(indice, CALIBRACION_NIEBLA)
    if vis < 1000:
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
        elif capa:
            break
        elif x["z"] > 1200:   # la capa tiene que empezar abajo
            break
    if not capa:
        return None
    techo = capa[-1]
    siguiente = next((x for x in niveles if x["z"] > techo["z"]), None)
    techo_m = techo["z"] + (0.5 * (siguiente["z"] - techo["z"]) if siguiente else 100)
    inversion = (siguiente["t"] - techo["t"]) if siguiente and siguiente.get("t") is not None else 0.0
    return {"techo": techo_m, "cobertura": max(x.get("nubes") or 0 for x in capa), "inversion": inversion}


def nota_niebla(madrugada: list[dict], elevacion_spot: float | None = None,
                capa: dict | None = None, tipo: str | None = None,
                bajas_spot: float | None = None) -> Nota:
    """Niebla y mar de nubes al amanecer: dos escenarios y se queda el mejor.

    - Niebla en el spot (radiación): fotogénica en embalses, ríos, bosques; en miradores y cumbres
      significa estar dentro de la nube y no ver nada.
    - Mar de nubes: el spot queda por encima del techo de la capa de nubes bajas/niebla del llano
      (perfil vertical del modelo), con inversión encima que la deja plana.
    """
    if not madrugada:
        return Nota(0.0, "Base: sin datos de madrugada")
    p, det = prob_niebla_radiacion(madrugada)
    lluvia = max(_v(x, "precipitation_probability") for x in madrugada)
    vista = (tipo or "") in TIPOS_VISTA

    a = Nota(0.0, "Base: sin niebla")
    if p >= 0.02:
        # ~50 % de probabilidad real ya es una apuesta excelente: la niebla nunca es segura
        a.suma(f"Niebla probable en el spot: {p * 100:.0f} % (humedad máx. {det['humedad']:.0f} %, "
               f"viento mín. {det['viento']:.0f} km/h)", 9.0 * min(1.0, p / 0.5))
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
            b.suma(f"Capa nubosa en valles y llano: {capa['cobertura']:.0f} %",
                   3.5 * _clamp((capa["cobertura"] - 50) / 45))
            if capa["inversion"] >= 1:
                b.suma(f"Inversión térmica de {capa['inversion']:.0f} °C encima: mar plano y estable",
                       min(1.5, 0.5 * capa["inversion"]))
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
