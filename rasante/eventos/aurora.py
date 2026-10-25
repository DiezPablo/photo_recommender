"""Auroras en España: pronóstico del índice Kp a 3 días (NOAA SWPC).

Desde España las auroras solo se ven (sobre todo en fotos, mirando al norte) en tormentas geomagnéticas
fuertes: con Kp 7 en el norte peninsular y con Kp 8-9 en casi todo el país (mayo y octubre de 2024).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import requests

from rasante.comun.red import sesion

URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"
FUENTE = "https://www.swpc.noaa.gov/products/3-day-forecast"
# horas UTC que son de noche cerrada en la península (aprox. 20-06 h locales todo el año)
NOCHE_UTC = {18, 21, 0, 3}
KP_NORTE = 7.0
KP_ESPANA = 8.0


def _filas(datos) -> list[tuple[datetime, float, str]]:
    """Admite el formato actual (lista de objetos) y el antiguo (lista de listas con cabecera)."""
    filas = []
    if datos and isinstance(datos[0], list):
        cab = datos[0]
        datos = [dict(zip(cab, f, strict=False)) for f in datos[1:]]
    for f in datos:
        t = datetime.fromisoformat(str(f["time_tag"]).replace(" ", "T")).replace(tzinfo=UTC)
        filas.append((t, float(f["kp"]), str(f.get("observed", ""))))
    return filas


def _noche(t: datetime) -> str:
    """La noche a la que pertenece un instante: la fecha de la tarde en que empieza."""
    return (t - timedelta(hours=12)).date().isoformat()


def resumen(datos, ahora: datetime) -> dict:
    """Kp máximo previsto de noche para las próximas noches y el nivel de aviso."""
    noches: dict[str, float] = {}
    for t, kp, _ in _filas(datos):
        # se cuenta el intervalo de 3 h que aún no ha terminado
        if t + timedelta(hours=3) <= ahora or t.hour not in NOCHE_UTC:
            continue
        n = _noche(t)
        noches[n] = max(noches.get(n, 0.0), kp)
    lista = [{"noche": n, "kp": round(kp, 2)} for n, kp in sorted(noches.items())]
    maximo = max(lista, key=lambda x: x["kp"], default=None)
    kp = maximo["kp"] if maximo else 0.0
    nivel = "espana" if kp >= KP_ESPANA else ("norte" if kp >= KP_NORTE else "ninguno")
    return {
        "actualizado": ahora.isoformat(timespec="minutes"),
        "noches": lista,
        "nivel": nivel,
        "noche": maximo["noche"] if maximo and nivel != "ninguno" else None,
        "kp_max": kp,
        "fuente": FUENTE,
    }


def aurora(ahora: datetime | None = None) -> dict | None:
    """Resumen con el pronóstico actual; None si NOAA no responde (el calendario sale igual)."""
    try:
        r = sesion().get(URL, timeout=30)
        r.raise_for_status()
        return resumen(r.json(), ahora or datetime.now(UTC))
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"  sin pronóstico de auroras: {e}")
        return None
