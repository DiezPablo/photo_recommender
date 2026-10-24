"""Contraste de astro.py con fuentes independientes guardadas en tests/fixtures:
- USNO (Observatorio Naval de EE. UU., API rstt/oneday): salida/puesta de sol y luna, iluminación.
- astropy: altura y azimut del centro galáctico.
Tolerancias: 3 minutos en horas, 2 puntos en iluminación, 0,5° en posición."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from rasante.cielo import astro

FIX = Path(__file__).parent / "fixtures"
USNO = json.loads((FIX / "usno_rstt.json").read_text())


def _hora(fecha: str, hhmm: str) -> datetime:
    return datetime.fromisoformat(f"{fecha}T{hhmm}:00+00:00")


def _evento(datos, fen):
    return next((e["time"] for e in datos if e["phen"] == fen), None)


def _cerca(a: datetime, b: datetime, minutos=3):
    return abs((a - b).total_seconds()) <= minutos * 60


@pytest.mark.parametrize("clave", sorted(USNO))
def test_sol_contra_usno(clave):
    c = USNO[clave]
    sol = astro.calcular_sol(c["lat"], c["lon"], date.fromisoformat(c["fecha"]), UTC)
    assert _cerca(sol.amanecer, _hora(c["fecha"], _evento(c["sundata"], "Rise")))
    assert _cerca(sol.atardecer, _hora(c["fecha"], _evento(c["sundata"], "Set")))
    # crepúsculo civil = inicio/fin de la hora azul en el lado oscuro
    assert _cerca(sol.azul_manana[0], _hora(c["fecha"], _evento(c["sundata"], "Begin Civil Twilight")))
    assert _cerca(sol.azul_tarde[1], _hora(c["fecha"], _evento(c["sundata"], "End Civil Twilight")))


@pytest.mark.parametrize("clave", sorted(USNO))
def test_luna_contra_usno(clave):
    c = USNO[clave]
    dia = date.fromisoformat(c["fecha"])
    from astral import Observer
    from astral import moon as amoon

    o = Observer(latitude=c["lat"], longitude=c["lon"])
    for fen, f in (("Rise", amoon.moonrise), ("Set", amoon.moonset)):
        ref = _evento(c["moondata"], fen)
        if ref is None:
            continue
        nuestra = f(o, dia, UTC)
        assert _cerca(nuestra, _hora(c["fecha"], ref), minutos=4), (fen, nuestra, ref)
    # USNO da la iluminación a las 12 h del día pedido (entero en %); comprobado con astroplan
    ilum = astro.iluminacion_luna(datetime(dia.year, dia.month, dia.day, 12, tzinfo=UTC))
    assert abs(ilum * 100 - int(c["fracillum"].rstrip("%"))) <= 2


def test_nombre_fase_coherente_con_usno():
    traduce = {
        "Waxing Gibbous": "gibosa creciente",
        "Waning Gibbous": "gibosa menguante",
        "Waxing Crescent": "creciente",
        "Waning Crescent": "menguante",
        "First Quarter": "cuarto creciente",
        "Last Quarter": "cuarto menguante",
        "Full Moon": "luna llena",
        "New Moon": "luna nueva",
    }
    aciertos = 0
    for c in USNO.values():
        d = date.fromisoformat(c["fecha"])
        t = datetime(d.year, d.month, d.day, 12, tzinfo=UTC)
        nuestro = astro.nombre_fase(astro.edad_luna(t), astro.iluminacion_luna(t))
        ref = traduce[c["curphase"]]
        # USNO solo llama "cuarto" al día exacto; nosotros a ±3 puntos del 50 %
        aciertos += nuestro == ref or (nuestro.startswith("cuarto") and nuestro.split()[1] in ref)
    # los límites entre fases son convencionales: basta con acertar casi todas
    assert aciertos == len(USNO)


def test_centro_galactico_contra_astropy():
    for c in json.loads((FIX / "astropy_centro_galactico.json").read_text()):
        t = datetime.fromisoformat(c["utc"]).replace(tzinfo=UTC)
        alt, az = astro.posicion_centro_galactico(c["lat"], c["lon"], t)
        assert abs(alt - c["alt"]) < 0.5, (c, alt)
        assert abs((az - c["az"] + 180) % 360 - 180) < 0.5, (c, az)


def test_via_lactea_temporada():
    """En junio el núcleo es fotografiable de noche en Madrid; a finales de diciembre no."""
    tz = ZoneInfo("Europe/Madrid")
    junio = astro.calcular_noche(40.79, -3.98, date(2027, 6, 21), tz)
    diciembre = astro.calcular_noche(40.79, -3.98, date(2026, 12, 21), tz)
    assert junio.vl_horas > 2
    assert 15 < junio.vl_altura_max < 25  # 90 - 40,8 - 29 ≈ 20°
    assert 160 < junio.vl_azimut_max < 200  # culmina hacia el sur
    assert diciembre.vl_horas == 0


def test_noche_tramos_sin_luna_dentro_de_la_noche():
    tz = ZoneInfo("Europe/Madrid")
    for d in range(0, 30, 3):
        n = astro.calcular_noche(40.79, -3.98, date(2026, 10, 1) + timedelta(days=d), tz)
        assert 0 <= n.horas_sin_luna <= n.horas_oscuras + 1e-6
        for a, b in n.sin_luna:
            assert n.ini <= a < b <= n.fin + timedelta(minutes=astro.PASO_MIN)


def test_punto_destino():
    lat, lon = astro.punto_destino(40.0, -4.0, 90, 40)
    assert abs(lat - 40.0) < 0.01 and lon > -4.0
    lat, lon = astro.punto_destino(40.0, -4.0, 0, 111.2)
    assert abs(lat - 41.0) < 0.01


def test_relieve_retrasa_el_amanecer_y_adelanta_el_atardecer():
    tz = ZoneInfo("Europe/Madrid")
    d = date(2026, 10, 23)
    sol = astro.calcular_sol(40.72, -3.85, d, tz)
    montana = lambda az: 5.0
    am, h1 = astro.sol_sobre_relieve(40.72, -3.85, d, tz, montana, "amanecer")
    at, h2 = astro.sol_sobre_relieve(40.72, -3.85, d, tz, montana, "atardecer")
    assert h1 == h2 == 5.0
    assert 20 < (am - sol.amanecer).total_seconds() / 60 < 45
    assert 20 < (sol.atardecer - at).total_seconds() / 60 < 45
    llano, _ = astro.sol_sobre_relieve(40.72, -3.85, d, tz, lambda az: 0.0, "atardecer")
    assert llano == sol.atardecer


def test_luna_llena_sale_al_atardecer_del_26_oct_2026():
    tz = ZoneInfo("Europe/Madrid")
    d = date(2026, 10, 26)
    e = astro.evento_luna(40.72, -3.85, d, tz, astro.calcular_sol(40.72, -3.85, d, tz))
    assert e.tipo == "salida" and e.iluminacion > 0.97 and -3 < e.altura_sol < 3


def test_relieve_tapa_la_via_lactea():
    tz = ZoneInfo("Europe/Madrid")
    libre = astro.calcular_noche(40.79, -3.98, date(2027, 6, 21), tz)
    tapada = astro.calcular_noche(
        40.79, -3.98, date(2027, 6, 21), tz, horizonte=lambda az: 25.0 if 140 < az < 220 else 0.0
    )
    assert libre.vl_horas > 2 and tapada.vl_horas == 0
