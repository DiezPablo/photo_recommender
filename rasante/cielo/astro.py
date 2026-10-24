"""
Cálculos astronómicos para fotografía: sol, luna y núcleo de la Vía Láctea.

- Sol: astral (salida/puesta, azimut, hora dorada y azul, noche astronómica).
- Luna: posición, salida y puesta con astral; iluminación con la fórmula de baja
  precisión de Meeus (cap. 48), error < 1 %.
- Vía Láctea: posición del centro galáctico (Sgr A*) calculada aquí con tiempo
  sidéreo y precesión aproximada; error < 0,5° (comprobado contra astropy en tests).

Todas las horas se devuelven como datetime con zona horaria.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from astral import Observer
from astral import moon as amoon
from astral import sun as asun

# Centro galáctico (Sgr A*), J2000
GC_RA_J2000 = 266.41683  # grados
GC_DEC_J2000 = -29.00781  # grados
ALTURA_MIN_VIA_LACTEA = 10.0  # por debajo la absorción y la contaminación del horizonte la borran
PASO_MIN = 10  # resolución de los muestreos nocturnos
MES_SINODICO = 29.530588


# ------------------------------------------------------------------ sol ----
@dataclass
class Sol:
    amanecer: datetime | None
    atardecer: datetime | None
    az_amanecer: float | None
    az_atardecer: float | None
    dorada_manana: tuple[datetime, datetime] | None
    dorada_tarde: tuple[datetime, datetime] | None
    azul_manana: tuple[datetime, datetime] | None
    azul_tarde: tuple[datetime, datetime] | None
    noche_ini: datetime | None  # fin del crepúsculo astronómico (sol a -18°) de esta tarde
    noche_fin: datetime | None  # inicio del crepúsculo astronómico de la mañana siguiente


def _seguro(f, *a, **k):
    try:
        return f(*a, **k)
    except ValueError:  # el sol no llega a esa altura ese día (latitudes altas)
        return None


def calcular_sol(lat: float, lon: float, dia: date, tz: ZoneInfo) -> Sol:
    o = Observer(latitude=lat, longitude=lon)
    amanecer = _seguro(asun.sunrise, o, dia, tz)
    atardecer = _seguro(asun.sunset, o, dia, tz)
    return Sol(
        amanecer=amanecer,
        atardecer=atardecer,
        az_amanecer=asun.azimuth(o, amanecer) if amanecer else None,
        az_atardecer=asun.azimuth(o, atardecer) if atardecer else None,
        dorada_manana=_seguro(asun.golden_hour, o, dia, asun.SunDirection.RISING, tz),
        dorada_tarde=_seguro(asun.golden_hour, o, dia, asun.SunDirection.SETTING, tz),
        azul_manana=_seguro(asun.blue_hour, o, dia, asun.SunDirection.RISING, tz),
        azul_tarde=_seguro(asun.blue_hour, o, dia, asun.SunDirection.SETTING, tz),
        noche_ini=_seguro(asun.dusk, o, dia, depression=18, tzinfo=tz),
        noche_fin=_seguro(asun.dawn, o, dia + timedelta(days=1), depression=18, tzinfo=tz),
    )


# ----------------------------------------------------------------- luna ----
def _jd(t: datetime) -> float:
    t = t.astimezone(UTC)
    return t.timestamp() / 86400.0 + 2440587.5


def iluminacion_luna(t: datetime) -> float:
    """Fracción iluminada del disco lunar (0-1). Meeus, Astronomical Algorithms, cap. 48."""
    T = (_jd(t) - 2451545.0) / 36525
    D = math.radians((297.8501921 + 445267.1114034 * T) % 360)
    M = math.radians((357.5291092 + 35999.0502909 * T) % 360)
    Mp = math.radians((134.9633964 + 477198.8675055 * T) % 360)
    i = (
        180
        - math.degrees(D)
        - 6.289 * math.sin(Mp)
        + 2.100 * math.sin(M)
        - 1.274 * math.sin(2 * D - Mp)
        - 0.658 * math.sin(2 * D)
        - 0.214 * math.sin(2 * Mp)
        - 0.110 * math.sin(D)
    )
    return (1 + math.cos(math.radians(i))) / 2


def edad_luna(t: datetime) -> float:
    """Días desde la última luna nueva (0 = nueva, ~14,8 = llena)."""
    # Luna nueva de referencia: 6 ene 2000 18:14 UTC
    return (_jd(t) - 2451550.26) % MES_SINODICO


def nombre_fase(edad: float, iluminacion: float) -> str:
    """Nombre de la fase según la iluminación (como USNO) y si crece o mengua."""
    creciente = edad < MES_SINODICO / 2
    if iluminacion < 0.03:
        return "luna nueva"
    if iluminacion > 0.97:
        return "luna llena"
    if 0.47 <= iluminacion <= 0.53:
        return "cuarto creciente" if creciente else "cuarto menguante"
    if iluminacion < 0.5:
        return "creciente" if creciente else "menguante"
    return "gibosa creciente" if creciente else "gibosa menguante"


def altura_luna(lat: float, lon: float, t: datetime) -> float:
    return amoon.elevation(Observer(latitude=lat, longitude=lon), t)


def azimut_luna(lat: float, lon: float, t: datetime) -> float:
    return amoon.azimuth(Observer(latitude=lat, longitude=lon), t)


def _evento_luna(f, o, dia, tz):
    try:
        return f(o, dia, tz)
    except ValueError:  # ese día la luna no sale o no se pone
        return None


# ------------------------------------------------------- centro galáctico --
def _gmst_grados(t: datetime) -> float:
    jd = _jd(t)
    T = (jd - 2451545.0) / 36525
    g = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * T * T - T**3 / 38710000
    return g % 360


def _precesar(ra: float, dec: float, t: datetime) -> tuple[float, float]:
    """Precesión J2000 → fecha (Meeus cap. 21, fórmula rigurosa con ζ, z, θ)."""
    T = (_jd(t) - 2451545.0) / 36525
    zeta = math.radians((2306.2181 * T + 0.30188 * T * T) / 3600)
    z = math.radians((2306.2181 * T + 1.09468 * T * T) / 3600)
    theta = math.radians((2004.3109 * T - 0.42665 * T * T) / 3600)
    ra0, dec0 = math.radians(ra), math.radians(dec)
    A = math.cos(dec0) * math.sin(ra0 + zeta)
    B = math.cos(theta) * math.cos(dec0) * math.cos(ra0 + zeta) - math.sin(theta) * math.sin(dec0)
    C = math.sin(theta) * math.cos(dec0) * math.cos(ra0 + zeta) + math.cos(theta) * math.sin(dec0)
    return (math.degrees(math.atan2(A, B) + z) % 360, math.degrees(math.asin(C)))


def posicion_centro_galactico(lat: float, lon: float, t: datetime) -> tuple[float, float]:
    """(altura, azimut) en grados del núcleo de la Vía Láctea. Azimut desde el norte, hacia el este.
    Sin refracción (a más de 10° de altura es menor de 0,1°)."""
    ra, dec = _precesar(GC_RA_J2000, GC_DEC_J2000, t)
    H = math.radians((_gmst_grados(t) + lon - ra) % 360)
    phi, d = math.radians(lat), math.radians(dec)
    alt = math.asin(math.sin(phi) * math.sin(d) + math.cos(phi) * math.cos(d) * math.cos(H))
    az = math.atan2(math.sin(H), math.cos(H) * math.sin(phi) - math.tan(d) * math.cos(phi))
    return math.degrees(alt), (math.degrees(az) + 180) % 360


# ---------------------------------------------------------- la noche ----
@dataclass
class Noche:
    """Resumen astronómico de la noche que empieza la tarde de `dia`."""

    ini: datetime | None
    fin: datetime | None
    horas_oscuras: float = 0.0
    luna_iluminacion: float = 0.0
    luna_edad: float = 0.0
    luna_fase: str = ""
    luna_salida: datetime | None = None
    luna_puesta: datetime | None = None
    # tramos de noche astronómica con la luna bajo el horizonte
    sin_luna: list[tuple[datetime, datetime]] = field(default_factory=list)
    horas_sin_luna: float = 0.0
    frac_luna_arriba: float = 0.0
    # núcleo de la Vía Láctea: tramos de noche astronómica con el núcleo por encima de 10°
    vl_tramos: list[tuple[datetime, datetime]] = field(default_factory=list)
    vl_horas: float = 0.0
    vl_horas_sin_luna: float = 0.0  # fotografiable de verdad: noche, núcleo alto y sin luna
    vl_altura_max: float | None = None
    vl_azimut_max: float | None = None
    vl_hora_max: datetime | None = None
    vl_azimut_ini: float | None = None
    vl_azimut_fin: float | None = None


def _tramos(muestras: list[tuple[datetime, bool]], paso: timedelta) -> list[tuple[datetime, datetime]]:
    tramos, ini = [], None
    for t, ok in muestras:
        if ok and ini is None:
            ini = t
        elif not ok and ini is not None:
            tramos.append((ini, t))
            ini = None
    if ini is not None:
        tramos.append((ini, muestras[-1][0] + paso))
    return tramos


def calcular_noche(lat: float, lon: float, dia: date, tz: ZoneInfo, sol: Sol | None = None, horizonte=None) -> Noche:
    """horizonte: función azimut → ángulo del relieve (grados), o None si el horizonte es plano.
    Con relieve, la luna tras una montaña no ilumina el cielo y el núcleo de la Vía Láctea tiene que
    asomar 2° por encima de las crestas."""
    sol = sol or calcular_sol(lat, lon, dia, tz)
    hz = horizonte or (lambda az: 0.0)
    o = Observer(latitude=lat, longitude=lon)
    mediodia = datetime(dia.year, dia.month, dia.day, 12, tzinfo=tz)
    medianoche = mediodia + timedelta(hours=12)
    edad, ilum = edad_luna(medianoche), iluminacion_luna(medianoche)
    n = Noche(
        ini=sol.noche_ini, fin=sol.noche_fin, luna_iluminacion=ilum, luna_edad=edad, luna_fase=nombre_fase(edad, ilum)
    )
    # Salida y puesta de la luna relevantes para esta noche: entre el mediodía y el mediodía siguiente
    eventos_salida = [_evento_luna(amoon.moonrise, o, d, tz) for d in (dia, dia + timedelta(days=1))]
    eventos_puesta = [_evento_luna(amoon.moonset, o, d, tz) for d in (dia, dia + timedelta(days=1))]
    fin_ventana = mediodia + timedelta(days=1)
    n.luna_salida = next((e for e in eventos_salida if e and mediodia <= e < fin_ventana), None)
    n.luna_puesta = next((e for e in eventos_puesta if e and mediodia <= e < fin_ventana), None)
    if not (sol.noche_ini and sol.noche_fin):
        return n

    paso = timedelta(minutes=PASO_MIN)
    muestras_luna, muestras_vl, muestras_vl_oscuro = [], [], []
    t = sol.noche_ini
    while t < sol.noche_fin:
        luna_abajo = amoon.elevation(o, t) < max(-0.5, hz(amoon.azimuth(o, t)))
        alt_vl, az_vl = posicion_centro_galactico(lat, lon, t)
        vl = alt_vl >= max(ALTURA_MIN_VIA_LACTEA, hz(az_vl) + 2)
        muestras_luna.append((t, luna_abajo))
        muestras_vl.append((t, vl))
        muestras_vl_oscuro.append((t, vl and luna_abajo))
        if vl and (n.vl_altura_max is None or alt_vl > n.vl_altura_max):
            n.vl_altura_max, n.vl_azimut_max, n.vl_hora_max = alt_vl, az_vl, t
        t += paso
    horas = lambda tramos: sum((b - a).total_seconds() for a, b in tramos) / 3600
    n.horas_oscuras = (sol.noche_fin - sol.noche_ini).total_seconds() / 3600
    n.sin_luna = _tramos(muestras_luna, paso)
    n.horas_sin_luna = min(horas(n.sin_luna), n.horas_oscuras)
    n.frac_luna_arriba = 1 - n.horas_sin_luna / n.horas_oscuras if n.horas_oscuras else 0.0
    n.vl_tramos = _tramos(muestras_vl, paso)
    n.vl_horas = horas(n.vl_tramos)
    n.vl_horas_sin_luna = horas(_tramos(muestras_vl_oscuro, paso))
    if n.vl_tramos:
        n.vl_azimut_ini = posicion_centro_galactico(lat, lon, n.vl_tramos[0][0])[1]
        n.vl_azimut_fin = posicion_centro_galactico(lat, lon, n.vl_tramos[-1][1])[1]
    return n


# ------------------------------------------------------- relieve y luna ----
def sol_sobre_relieve(
    lat: float, lon: float, dia: date, tz: ZoneInfo, horizonte, momento: str
) -> tuple[datetime | None, float | None]:
    """Hora a la que el sol asoma (amanecer) o se esconde (atardecer) tras el relieve, y el ángulo del
    horizonte en ese punto. El azimut cambia con la altura, así que se itera dos veces."""
    o = Observer(latitude=lat, longitude=lon)
    direccion = asun.SunDirection.RISING if momento == "amanecer" else asun.SunDirection.SETTING
    t = _seguro(asun.sunrise if momento == "amanecer" else asun.sunset, o, dia, tz)
    if t is None:
        return None, None
    h = 0.0
    for _ in range(2):
        h = max(0.0, horizonte(asun.azimuth(o, t)))
        if h <= 0.3:
            return t, h
        t2 = _seguro(asun.time_at_elevation, o, h, dia, direccion, tz)
        if t2 is None:  # el sol no llega a superar el relieve ese día
            return None, h
        t = t2
    return t, h


@dataclass
class EventoLuna:
    tipo: str  # "salida" (luna llena al anochecer) o "puesta" (al amanecer)
    hora: datetime  # cuando asoma sobre el relieve / se esconde tras él
    azimut: float
    horizonte: float  # ángulo del relieve en ese azimut
    iluminacion: float
    altura_sol: float  # altura del sol en ese momento: entre -6° y +2° el paisaje y la luna se equilibran


def evento_luna(lat: float, lon: float, dia: date, tz: ZoneInfo, sol: Sol, horizonte=None) -> EventoLuna | None:
    """Salida de la luna cerca del atardecer o puesta cerca del amanecer (± 75 min): la foto de la
    luna grande sobre el paisaje con luz de crepúsculo. Devuelve el mejor evento del día o None."""
    hz = horizonte or (lambda az: 0.0)
    o = Observer(latitude=lat, longitude=lon)
    candidatos = []
    for tipo, f, ref in (("salida", amoon.moonrise, sol.atardecer), ("puesta", amoon.moonset, sol.amanecer)):
        if ref is None:
            continue
        for d in (dia - timedelta(days=1), dia, dia + timedelta(days=1)):
            t = _evento_luna(f, o, d, tz)
            if t is None or abs((t - ref).total_seconds()) > 3 * 3600:
                continue
            # momento en que la luna supera (o baja de) el relieve: paso de 2 min
            paso = timedelta(minutes=2 if tipo == "salida" else -2)
            for _ in range(120):
                az = amoon.azimuth(o, t)
                if amoon.elevation(o, t) >= max(0.0, hz(az)):
                    break
                t += paso
            if abs((t - ref).total_seconds()) > 75 * 60:
                continue
            ilum = iluminacion_luna(t)
            candidatos.append(
                EventoLuna(tipo, t, amoon.azimuth(o, t), max(0.0, hz(amoon.azimuth(o, t))), ilum, asun.elevation(o, t))
            )
    if not candidatos:
        return None
    return max(candidatos, key=lambda e: e.iluminacion - abs(e.altura_sol + 2) / 20)


def punto_destino(lat: float, lon: float, azimut_deg: float, km: float) -> tuple[float, float]:
    """Punto a `km` de (lat, lon) siguiendo el rumbo `azimut_deg` (0 = norte)."""
    R = 6371.0
    d = km / R
    b = math.radians(azimut_deg)
    la1, lo1 = math.radians(lat), math.radians(lon)
    la2 = math.asin(math.sin(la1) * math.cos(d) + math.cos(la1) * math.sin(d) * math.cos(b))
    lo2 = lo1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(la1), math.cos(d) - math.sin(la1) * math.sin(la2))
    return round(math.degrees(la2), 4), round(math.degrees(lo2), 4)
