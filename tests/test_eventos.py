"""Calendario de eventos: fases de la luna contra astropy, lluvias de meteoros, Vía Láctea y naturaleza."""

import json
from datetime import UTC, date, datetime

import pytest
from conftest import FIX, sin_nan

from rasante.eventos import aurora, cielo, naturaleza, starlight
from rasante.eventos.cli import generar

# Lunas nuevas y llenas calculadas con astropy (elongación mínima/máxima), en UTC
REFERENCIA = [
    ("2026-10-26T03:52", "llena"),
    ("2026-11-09T06:52", "nueva"),
    ("2026-11-24T15:02", "llena"),
    ("2026-12-09T01:16", "nueva"),
    ("2026-12-24T01:51", "llena"),
    ("2027-01-07T20:58", "nueva"),
    ("2027-01-22T12:32", "llena"),
    ("2027-02-06T15:57", "nueva"),
]


def test_fases_luna_contra_astropy():
    fases = cielo._extremos_iluminacion(date(2026, 10, 24), date(2027, 2, 10))
    assert [f for _, f in fases] == [f for _, f in REFERENCIA]
    for (t, _), (ref, _) in zip(fases, REFERENCIA, strict=True):
        error_min = abs((t.replace(tzinfo=None) - datetime.fromisoformat(ref)).total_seconds()) / 60
        assert error_min < 60, (t, ref)


def test_lluvias_de_meteoros_con_luna():
    lluvias = {m["id"]: m for m in cielo.lluvias_meteoros(date(2026, 10, 24), date(2027, 12, 31))}
    assert lluvias["geminidas-2026"]["fecha"] == "2026-12-14"
    assert lluvias["geminidas-2026"]["noche"] == "2026-12-13"  # la noche empieza la tarde anterior
    assert lluvias["geminidas-2026"]["calidad"] == "buena"  # luna creciente fina y ya puesta
    assert lluvias["liridas-2027"]["calidad"] == "mala"  # luna llena
    assert "orionidas-2026" not in lluvias  # ya pasó


def test_via_lactea_temporada_y_ventanas():
    vl = cielo.via_lactea(date(2026, 10, 24), date(2027, 10, 31))
    horas = vl["horas_por_mes"]
    assert horas.index(max(horas)) == 5  # junio
    assert horas[11] == 0 and horas[0] == 0  # en diciembre y enero el núcleo no sale de noche
    junio = next(v for v in vl["ventanas"] if v["luna_nueva"].startswith("2027-06"))
    assert junio["desde"] <= junio["luna_nueva"] <= junio["hasta"]
    assert junio["horas_max"] > 4


def test_eclipses_futuros():
    assert [e["fecha"] for e in cielo.eclipses(date(2026, 10, 24))] == ["2027-08-02", "2028-01-26"]


def test_naturaleza_valida():
    eventos = naturaleza.cargar()
    assert len(eventos) >= 40
    jerte = next(e for e in eventos if e["id"] == "cerezo-jerte")
    assert (jerte["provincia"], jerte["ccaa"]) == ("Cáceres", "Extremadura")
    assert all(e["ccaa"] for e in eventos), [e["id"] for e in eventos if not e["ccaa"]]


def test_naturaleza_rechaza_errores(tmp_path):
    malo = tmp_path / "e.csv"
    cabecera = "id,nombre,categoria,desde,hasta,pico,lugar,lat,lon,radio_km,descripcion,consejo\n"
    malo.write_text(cabecera + "x,X,volcanes,01-01,02-01,01-15,L,40,-3,5,d,c\n")
    with pytest.raises(ValueError, match="categoría"):
        naturaleza.cargar(malo)
    malo.write_text(cabecera + "x,X,flora,13-01,02-01,01-15,L,40,-3,5,d,c\n")
    with pytest.raises(ValueError, match="MM-DD"):
        naturaleza.cargar(malo)


def test_generar_sin_nan():
    datos = generar(date(2026, 10, 24), 13, con_red=False)
    sin_nan(datos)
    assert datos["luna"] and datos["meteoros"] and datos["naturaleza"]


def test_aurora_con_pronostico_real():
    datos = json.loads((FIX / "noaa_kp.json").read_text())
    r = aurora.resumen(datos, datetime(2026, 10, 25, 8, tzinfo=UTC))
    assert r["noches"][0]["noche"] == "2026-10-25"  # lo observado ya no cuenta
    assert all(n["kp"] < 7 for n in r["noches"])
    assert r["nivel"] == "ninguno" and r["noche"] is None


def test_aurora_tormenta_fuerte_y_formato_antiguo():
    # formato antiguo de NOAA: lista de listas con cabecera; Kp 8 de madrugada → aviso para toda España
    datos = [
        ["time_tag", "kp", "observed", "noaa_scale"],
        ["2024-05-10 21:00:00", "7.67", "predicted", "G3"],
        ["2024-05-11 00:00:00", "8.67", "predicted", "G4"],
        ["2024-05-11 12:00:00", "9.00", "predicted", "G5"],  # de día: no cuenta
    ]
    r = aurora.resumen(datos, datetime(2024, 5, 10, 12, tzinfo=UTC))
    assert r["nivel"] == "espana"
    assert r["noche"] == "2024-05-10"
    assert r["kp_max"] == 8.67


def test_starlight():
    zonas = starlight.cargar()
    assert sum(z["tipo"] == "reserva" for z in zonas) >= 22
    soria = next(z for z in zonas if z["id"] == "soria")
    assert soria["provincia"] == "Soria" and soria["radio_km"] is None
