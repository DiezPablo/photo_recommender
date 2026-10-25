"""Mar en la costa: mareas y oleaje con una respuesta real de Open-Meteo Marine (As Catedrales, mareas vivas)."""

import json
from datetime import date, datetime
from itertools import pairwise
from zoneinfo import ZoneInfo

import pandas as pd
from conftest import FIX

from rasante.prevision import mar
from rasante.prevision.openmeteo import a_tabla

TZ = ZoneInfo("Europe/Madrid")
DF = a_tabla(json.loads((FIX / "openmeteo_marine_catedrales.json").read_text()))["horas"]
DIA = date(2026, 10, 25)


def test_pleamares_y_bajamares():
    m = mar.dia(DF, DIA, TZ, {})
    tipos = [x["tipo"] for x in m["mareas"]]
    assert len(tipos) == 4 and all(a != b for a, b in pairwise(tipos))  # se alternan
    assert m["rango_m"] > 3  # Cantábrico con mareas vivas
    bajas = [x for x in m["mareas"] if x["tipo"] == "baja"]
    altas = [x for x in m["mareas"] if x["tipo"] == "alta"]
    assert max(b["m"] for b in bajas) < min(a["m"] for a in altas)
    # ~12 h 25 min entre dos bajamares
    h = [int(b["t"][:2]) * 60 + int(b["t"][3:]) for b in bajas]
    assert 11 * 60 < h[1] - h[0] < 13 * 60


def test_marea_y_olas_en_el_atardecer():
    t = datetime(2026, 10, 25, 19, 20, tzinfo=TZ)
    m = mar.dia(DF, DIA, TZ, {"atardecer": t})
    a = m["atardecer"]
    assert 0 <= a["marea"] <= 1 and isinstance(a["sube"], bool)
    assert a["olas_m"] > 0 and a["periodo_s"] > 0


def test_extremo_afinado_entre_horas():
    idx = pd.date_range("2026-01-01 00:00", periods=5, freq="h")
    # mínimo exacto a las 02:30: la parábola lo encuentra aunque la serie sea horaria
    serie = pd.Series([(h - 2.5) ** 2 for h in range(5)], index=idx)
    [(t, tipo, m)] = mar.extremos(serie)
    assert tipo == "baja" and t == pd.Timestamp("2026-01-01 02:30") and abs(m) < 1e-9


def test_mediterraneo_sin_indice_de_marea():
    plano = DF.copy()
    plano["sea_level_height_msl"] = plano["sea_level_height_msl"] * 0.05  # rango de pocos centímetros
    m = mar.dia(plano, DIA, TZ, {"atardecer": datetime(2026, 10, 25, 19, 20, tzinfo=TZ)})
    assert "marea" not in m["atardecer"] and m["rango_m"] < mar.MAREA_PEQUENA_M


def test_costa():
    costa = mar.Costa()
    assert costa.es_costero({"lat": 43.5536, "lon": -7.1573, "tipo": "playa"})  # As Catedrales
    assert not costa.es_costero({"lat": 40.8, "lon": -3.95, "tipo": "cumbre"})  # Peñalara
    assert not costa.es_costero({"lat": 40.793, "lon": -4.011, "tipo": "mirador"})  # Navacerrada, en la raya
    assert not costa.es_costero({"lat": 42.43, "lon": 1.49, "tipo": "mirador"})  # raya con Andorra
