"""Climatología: rejilla, resumen diario de ERA5 (respuesta real grabada) y probabilidades por mes."""

import json
import math

import pandas as pd
from conftest import FIX

from rasante.clima import agregar, era5, rejilla


def test_rejilla_cubre_espana():
    puntos = rejilla.puntos()
    assert 250 < len(puntos) < 350
    assert (40.5, -3.5) in puntos  # Madrid
    assert (28.5, -16.5) in puntos  # Tenerife
    assert (39.5, 3.0) in puntos  # Mallorca
    assert (38.0, 1.0) not in puntos  # mar abierto


def test_coste_de_las_peticiones():
    assert round(era5.coste()) == 130  # 5 años, 7 variables
    assert era5.coste(variables=12) > era5.coste()


def test_resumen_diario_con_era5_real():
    df = era5.horario(json.loads((FIX / "era5_madrid.json").read_text()))
    r = era5.resumir(df, 40.5, -4.0)
    assert len(r) >= 9
    fila = r.iloc[0]
    assert 115 < fila["az_am"] < 125 and 235 < fila["az_at"] < 245  # enero
    for c in ("am_bajas", "at_altas", "hr_max", "viento_min"):
        assert 0 <= fila[c] <= 100
    assert r["despejadas"].between(0, 16).all()


def test_guardar_y_leer(tmp_path):
    r = pd.DataFrame([{"fecha": "2025-01-01", "am_bajas": 12.34}])
    f = tmp_path / "x.csv.gz"
    era5.guardar(r, f)
    assert era5.leer(f).iloc[0]["am_bajas"] == 12.3


def _dia(fecha, bajas=0, medias=0, altas=50, despejadas=6, hr=80, viento=10):
    f = {"fecha": fecha, "az_am": 90.0, "az_at": 270.0, "hr_max": hr, "viento_min": viento, "despejadas": despejadas}
    for m in ("am", "at"):
        f.update(
            {
                f"{m}_bajas": bajas,
                f"{m}_medias": medias,
                f"{m}_altas": altas,
                f"{m}_lluvia": 0.0,
                f"{m}_humedad": 60.0,
                f"{m}_viento": 5.0,
            }
        )
    return f


def test_por_mes_con_rejilla_sintetica():
    # 3×3 puntos; enero con lienzo de altas y camino limpio, julio cubierto de bajas
    fechas = [f"2025-01-{d:02d}" for d in range(1, 11)] + [f"2025-07-{d:02d}" for d in range(1, 11)]
    resumenes = {}
    for la in (40.0, 40.5, 41.0):
        for lo in (-4.5, -4.0, -3.5):
            filas = [
                _dia(f) if f.startswith("2025-01") else _dia(f, bajas=100, altas=0, despejadas=0, hr=99, viento=1)
                for f in fechas
            ]
            resumenes[(la, lo)] = pd.DataFrame(filas)
    datos = agregar.cargar_datos(resumenes)
    notas = agregar.notas_punto(datos, 40.5, -4.0)
    m = agregar.por_mes(notas)
    assert all(len(v) == 12 for v in m.values())
    assert m["atardecer"][0] == 100 and m["atardecer"][6] == 0
    assert m["noche"][0] == 100 and m["noche"][6] == 0
    assert m["niebla"][6] > m["niebla"][0]
    assert m["amanecer"][3] is None  # abril: sin datos


def test_camino_por_vecinos_y_costa():
    datos = agregar.cargar_datos({(40.5, -4.0): pd.DataFrame([_dia("2025-01-01", bajas=80)])})
    # el punto de la rejilla
    assert agregar._valor_camino(datos, 40.5, -4.0, "2025-01-01", "at")["bajas"] == 80
    # cerca (< 0,35°) sin vecinos: el más cercano; lejos: nada
    assert agregar._valor_camino(datos, 40.6, -4.1, "2025-01-01", "at")["bajas"] == 80
    assert agregar._valor_camino(datos, 41.3, -4.0, "2025-01-01", "at") is None
    assert not math.isnan(agregar.notas_punto(datos, 40.5, -4.0)["atardecer"][0])
