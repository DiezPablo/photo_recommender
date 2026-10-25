"""Alineaciones: cuándo sale o se pone el sol (o la luna llena en el crepúsculo) justo por un pico del horizonte
de cada spot, en los próximos doce meses.

- Picos: máximos del perfil del horizonte del terreno (`spots.geojson`, cada 2°) con al menos 1° de
  prominencia y como mucho 15° de altura (más alto es la pared de un cañón); los tres más prominentes.
- Sol y luna: posición geocéntrica cada 10 min, común a todos los spots (sol con la fórmula de baja precisión
  de Meeus, luna con astral); por spot se pasa a altura y azimut con numpy, con paralaje (luna) y refracción.
  Contra astropy: < 0,1° (tests).
- Alineación: el astro cruza la altura del pico a menos de 1° de su azimut. El sol pasa varios días seguidos
  por el mismo pico: se da el mejor día y la ventana. La luna solo cuenta casi llena (≥ 85 %) y con el sol entre
  8° bajo el horizonte y 3° sobre él (la foto clásica: luna grande y paisaje con luz).
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
from astral.moon import moon_position

from rasante.cielo.astro import iluminacion_luna

PASO_MIN = 10
TOLERANCIA = 1.0  # grados de azimut
PROMINENCIA = 1.0  # grados
MAX_PICOS = 3
# más alto ya no es «salir por el pico» sino asomar por la pared de un cañón: otra foto
MAX_ALTURA_PICO = 15.0
LUNA_MIN = 0.85
SOL_CREPUSCULO = (-8.0, 3.0)
PARALAJE_LUNA = 0.95  # grados (paralaje horizontal media)


def zona(lon: float) -> ZoneInfo:
    return ZoneInfo("Atlantic/Canary" if lon < -12 else "Europe/Madrid")


# ------------------------------------------------------------------ efemérides ----
def instantes(desde: date, dias: int) -> np.ndarray:
    """Instantes UTC (segundos Unix) cada PASO_MIN minutos."""
    t0 = datetime(desde.year, desde.month, desde.day, tzinfo=UTC).timestamp() - 3 * 3600
    return t0 + np.arange(0, (dias + 1) * 86400, PASO_MIN * 60, dtype=float)


def _jd(t: np.ndarray) -> np.ndarray:
    return t / 86400.0 + 2440587.5


def gmst(t: np.ndarray) -> np.ndarray:
    """Tiempo sidéreo medio de Greenwich (grados)."""
    d = _jd(t) - 2451545.0
    return (280.46061837 + 360.98564736629 * d) % 360


def sol_radec(t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Ascensión recta y declinación aparentes del sol (grados), Meeus de baja precisión (~0,01°)."""
    T = (_jd(t) - 2451545.0) / 36525
    L0 = (280.46646 + T * (36000.76983 + 0.0003032 * T)) % 360
    M = np.radians(357.52911 + T * (35999.05029 - 0.0001537 * T))
    C = (1.914602 - T * (0.004817 + 0.000014 * T)) * np.sin(M) + (0.019993 - 0.000101 * T) * np.sin(2 * M)
    C += 0.000289 * np.sin(3 * M)
    omega = np.radians(125.04 - 1934.136 * T)
    lam = np.radians(L0 + C - 0.00569 - 0.00478 * np.sin(omega))
    eps = np.radians(23.439291 - 0.0130042 * T + 0.00256 * np.cos(omega))
    ra = np.degrees(np.arctan2(np.cos(eps) * np.sin(lam), np.cos(lam))) % 360
    dec = np.degrees(np.arcsin(np.sin(eps) * np.sin(lam)))
    return ra, dec


def luna_radec(t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Posición geocéntrica de la luna (astral, grados)."""
    ra = np.empty_like(t)
    dec = np.empty_like(t)
    for i, x in enumerate(t):
        p = moon_position(_jd(np.array(x)) - 2451545.0)
        ra[i], dec[i] = math.degrees(p.right_ascension) % 360, math.degrees(p.declination)
    return ra, dec


def altaz(lat: float, lon: float, ra: np.ndarray, dec: np.ndarray, gst: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Altura y azimut geocéntricos (grados; azimut desde el norte hacia el este)."""
    h = np.radians(gst + lon - ra)
    phi, d = math.radians(lat), np.radians(dec)
    alt = np.degrees(np.arcsin(math.sin(phi) * np.sin(d) + math.cos(phi) * np.cos(d) * np.cos(h)))
    az = np.degrees(np.arctan2(np.sin(h), np.cos(h) * math.sin(phi) - np.tan(d) * math.cos(phi))) + 180
    return alt, az % 360


def refraccion(alt: np.ndarray) -> np.ndarray:
    """Refracción atmosférica (grados) para una altura verdadera (Sæmundsson)."""
    a = np.maximum(alt, -1.0)
    return (1.02 / np.tan(np.radians(a + 10.3 / (a + 5.11)))) / 60


class Efemerides:
    """Sol y luna en una rejilla de instantes, para reutilizar en todos los spots."""

    def __init__(self, desde: date, dias: int = 365):
        self.desde, self.dias = desde, dias
        self.t = instantes(desde, dias)
        self.gst = gmst(self.t)
        self.sol = sol_radec(self.t)
        self.luna = luna_radec(self.t)


# ----------------------------------------------------------------------- picos ----
def picos(angulos: list[int]) -> list[tuple[float, float, float]]:
    """(azimut, altura, prominencia) de los picos del horizonte; `angulos` en décimas de grado."""
    a = np.array(angulos, dtype=float) / 10
    n = len(a)
    paso = 360 / n
    ventana = max(1, round(15 / paso))
    lista = []
    for i in range(n):
        izq = [a[(i - k) % n] for k in range(1, ventana + 1)]
        der = [a[(i + k) % n] for k in range(1, ventana + 1)]
        # máximo local (en una meseta, su primer punto)
        if a[i] < max(izq[0], der[0]) or a[i] == izq[0]:
            continue
        prominencia = a[i] - max(min(izq), min(der))
        if prominencia >= PROMINENCIA and a[i] <= MAX_ALTURA_PICO:
            lista.append((i * paso, float(a[i]), float(prominencia)))
    return sorted(lista, key=lambda p: -p[2])[:MAX_PICOS]


# ------------------------------------------------------------------ alineaciones ----
def _cruces(alt: np.ndarray, az: np.ndarray, altura: float):
    """Instantes (índice fraccional) y azimut en que la altura aparente cruza `altura`, y si sube o baja."""
    f = alt - altura
    k = np.nonzero(np.sign(f[:-1]) != np.sign(f[1:]))[0]
    for i in k:
        w = f[i] / (f[i] - f[i + 1])
        yield i + w, az[i] + (az[i + 1] - az[i]) * w, f[i + 1] > f[i]


def alineaciones_spot(ef: Efemerides, lat: float, lon: float, angulos: list[int]) -> list[dict]:
    tz = zona(lon)
    sol_alt, sol_az = altaz(lat, lon, *ef.sol, ef.gst)
    sol_alt = sol_alt + refraccion(sol_alt)
    lun_alt, lun_az = altaz(lat, lon, *ef.luna, ef.gst)
    lun_alt = lun_alt - PARALAJE_LUNA * np.cos(np.radians(lun_alt))
    lun_alt = lun_alt + refraccion(lun_alt)

    def instante(x: float) -> datetime:
        return datetime.fromtimestamp(float(np.interp(x, np.arange(len(ef.t)), ef.t)), UTC).astimezone(tz)

    def hasta_hoy(d: datetime) -> bool:
        return ef.desde <= d.date() < ef.desde + timedelta(days=ef.dias)

    resultado = []
    for az_p, h_p, _ in picos(angulos):
        # sol: días seguidos por el mismo pico → una ventana con su mejor día
        dias: list[tuple[datetime, float, bool, float]] = []
        for x, az, sube in _cruces(sol_alt, sol_az, h_p):
            if abs(az - az_p) <= TOLERANCIA:
                t = instante(x)
                if hasta_hoy(t):
                    dias.append((t, az, sube, abs(az - az_p)))
        grupos: list[list] = []
        for d in sorted(dias, key=lambda x: x[0]):
            if grupos and grupos[-1][-1][2] == d[2] and (d[0] - grupos[-1][-1][0]) <= timedelta(days=1.5):
                grupos[-1].append(d)
            else:
                grupos.append([d])
        for g in grupos:
            mejor = min(g, key=lambda x: x[3])
            resultado.append(
                {
                    "cuerpo": "sol",
                    "evento": "sale" if mejor[2] else "se pone",
                    "fecha": mejor[0].date().isoformat(),
                    "hora": mejor[0].strftime("%H:%M"),
                    "desde": g[0][0].date().isoformat(),
                    "hasta": g[-1][0].date().isoformat(),
                    "azimut": round(az_p, 1),
                    "altura": round(h_p, 1),
                }
            )
        # luna casi llena en el crepúsculo
        for x, az, sube in _cruces(lun_alt, lun_az, h_p):
            if abs(az - az_p) > TOLERANCIA:
                continue
            i = round(x)
            if not (SOL_CREPUSCULO[0] <= sol_alt[min(i, len(sol_alt) - 1)] <= SOL_CREPUSCULO[1]):
                continue
            t = instante(x)
            ilum = iluminacion_luna(t)
            if ilum < LUNA_MIN or not hasta_hoy(t):
                continue
            resultado.append(
                {
                    "cuerpo": "luna",
                    "evento": "sale" if sube else "se pone",
                    "fecha": t.date().isoformat(),
                    "hora": t.strftime("%H:%M"),
                    "iluminacion": round(ilum * 100),
                    "azimut": round(az_p, 1),
                    "altura": round(h_p, 1),
                }
            )
    return sorted(resultado, key=lambda r: (r["fecha"], r["hora"]))


def calcular(spots: list[dict], desde: date, dias: int = 365) -> dict[str, list[dict]]:
    """{id del spot: alineaciones} para los spots con perfil del horizonte."""
    ef = Efemerides(desde, dias)
    salida = {}
    for s in spots:
        h = s.get("horizonte")
        if not h or not h.get("angulos"):
            continue
        a = alineaciones_spot(ef, s["lat"], s["lon"], h["angulos"])
        if a:
            salida[s["id"]] = a
    return salida
