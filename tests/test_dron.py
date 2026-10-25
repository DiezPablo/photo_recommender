"""Dron: zonas reales de ENAIRE y de la Agencia Europea de Medio Ambiente (grabadas y simplificadas)."""

import json

from conftest import FIX

from rasante.dron.cli import Capa, calcular
from rasante.dron.zonas import clasificar, texto_plano

GRABADO = json.loads((FIX / "dron_zonas.json").read_text())
CAPAS = [Capa(nombre, fs) for nombre, fs in GRABADO["capas"].items()]


def _spots(*nombres):
    return [{"id": n, "lat": GRABADO["puntos"][n][0], "lon": GRABADO["puntos"][n][1]} for n in nombres]


def test_estado_de_cada_punto():
    d = calcular(_spots("ordesa", "barajas", "gallocanta", "madrid_tma", "fotografico"), CAPAS)
    estado = {k: v["estado"] for k, v in d["spots"].items()}
    assert estado["ordesa"] == "no"  # parque nacional
    assert estado["barajas"] == "no"  # junto al aeropuerto
    assert estado["gallocanta"] == "permiso"  # espacio protegido (y Red Natura)
    assert estado["fotografico"] == "permiso"  # zona restringida al vuelo fotográfico (Defensa)
    # la zona más restrictiva va primero
    ordesa = [d["zonas"][z] for z in d["spots"]["ordesa"]["zonas"]]
    assert ordesa[0]["nivel"] == "no"
    assert {z["capa"] for z in ordesa} >= {"protegido", "natura"}


def test_zonas_por_encima_de_120_m_no_cuentan():
    tma = {"type": "REQ_AUTHORIZATION", "reasons": "AIR_TRAFFIC", "lower": 305, "lowerReference": "AGL", "uom": "M"}
    assert clasificar("aero", tma) is None
    pies = {**tma, "lower": 500, "uom": "FT"}  # 152 m
    assert clasificar("aero", pies) is None
    bajo = {**tma, "lower": 45, "upper": 900, "name": "VIGO", "message": "<p>Por debajo de 45m…</p>"}
    z = clasificar("aero", bajo)
    assert z["nivel"] == "condiciones" and z["desde_m"] == 45 and z["hasta_m"] is None


def test_sin_zonas_es_libre():
    d = calcular([{"id": "campo", "lat": 41.5, "lon": -2.9}], CAPAS)
    assert d["spots"]["campo"] == {"estado": "libre"}


def test_texto_plano():
    t = texto_plano('Zona.<p>Por debajo de <b>45m</b> &amp; más</p><p><font color="#f00">NO</font></p>')
    assert t == "Zona.\nPor debajo de 45m & más\nNO"
