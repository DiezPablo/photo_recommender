"""Previsión completa con respuestas reales de Open-Meteo grabadas (sin red) y JSON publicado válido."""

import json
from datetime import datetime

import pandas as pd
import pytest
from conftest import LP, sin_nan

from rasante.comun.ficheros import escribir_json
from rasante.prevision.openmeteo import NIVELES_HPA
from rasante.prevision.series import en, perfil_en
from rasante.prevision.spots import cargar_spots


def test_informe_con_respuestas_grabadas(informe, tmp_path):
    assert informe["modelo"] == "v2"
    assert [s["nombre"] for s in informe["spots"]] == ["Puerto de Navacerrada", "Faro de Fisterra"]
    for s in informe["spots"]:
        assert len(s["dias"]) == 3 and s["contaminacion"] == LP
        assert s["elevacion"] is not None
        for d in s["dias"]:
            assert set(d["notas"]) == {"amanecer", "atardecer", "astro", "niebla", "luna"}
            for n in d["notas"].values():
                assert 0 <= n["nota"] <= 10
                assert n["desglose"] and all("texto" in f and "puntos" in f for f in n["desglose"])
                assert abs(max(0, min(10, sum(f["puntos"] for f in n["desglose"]))) - n["nota"]) < 0.4
            for m in ("amanecer", "atardecer"):
                assert d["notas"][m]["confianza"] in ("alta", "media", "baja")
                assert [p["km"] for p in d["meteo"][m]["camino"]] == [15, 40, 80, 150]
            assert d["sol"]["amanecer"] < d["sol"]["atardecer"]
            assert 60 < d["sol"]["az_amanecer"] < 130 and 230 < d["sol"]["az_atardecer"] < 300
            assert d["meteo"]["noche"]["horas"], "falta la nubosidad hora a hora de la noche"
    assert informe["spots"][0]["dias"][2]["fiabilidad"] == "media"

    ruta = tmp_path / "informe.json"
    escribir_json(ruta, informe)
    texto = ruta.read_text()
    assert "NaN" not in texto and "Infinity" not in texto
    sin_nan(json.loads(texto))


def test_interpolacion_al_pico_de_color():
    idx = pd.date_range("2026-10-20 19:00", periods=2, freq="h")
    df = pd.DataFrame({"cloud_cover_low": [0.0, 100.0]}, index=idx)
    assert en(df, datetime(2026, 10, 20, 19, 15))["cloud_cover_low"] == pytest.approx(25)


def test_perfil_descarta_niveles_bajo_el_suelo():
    idx = pd.date_range("2026-10-20 08:00", periods=1, freq="h")
    fila = {}
    for p, z in zip(NIVELES_HPA, (100, 320, 540, 770, 1000, 1470, 1950, 3000), strict=True):
        fila.update(
            {
                f"geopotential_height_{p}hPa": z,
                f"temperature_{p}hPa": 5,
                f"relative_humidity_{p}hPa": 99,
                f"cloud_cover_{p}hPa": 90,
            }
        )
    df = pd.DataFrame([fila], index=idx)
    niveles = perfil_en(df, datetime(2026, 10, 20, 8), suelo=650)["niveles"]
    assert min(x["z"] for x in niveles) >= 680


def test_cargar_mis_spots_ignora_comentarios(tmp_path, monkeypatch):
    from rasante.prevision import spots as S

    monkeypatch.setattr(S, "_relieve", lambda lat, lon: None)
    csv = tmp_path / "mis.csv"
    csv.write_text("nombre,lat,lon,tipo\n# comentario\nMi sitio,40.5,-3.9,embalse\n")
    spots = cargar_spots(None, csv)
    assert len(spots) == 1 and spots[0]["tipo"] == "embalse" and spots[0]["origen"] == "propio"
    assert spots[0]["provincia"] == "Madrid" and spots[0]["ccaa"] == "Comunidad de Madrid"


def test_canarias_en_su_hora_y_series_sin_desfase():
    from datetime import datetime
    from zoneinfo import ZoneInfo

    import pandas as pd

    from rasante.prevision import series
    from rasante.prevision.evaluacion import zona_de

    madrid, canarias = ZoneInfo("Europe/Madrid"), ZoneInfo("Atlantic/Canary")
    assert zona_de(-16.3, madrid) == canarias
    assert zona_de(-3.7, madrid) == madrid
    # serie horaria en hora peninsular (como se pide a Open-Meteo): 19:00 en Tenerife son las 20:00 peninsulares
    df = pd.DataFrame({"x": [0.0, 10.0, 20.0]}, index=pd.date_range("2026-01-10 19:00", periods=3, freq="h"))
    series.ZONA_SERIES = madrid
    assert series.en(df, datetime(2026, 1, 10, 19, 0, tzinfo=canarias))["x"] == 10.0
    assert series.en(df, datetime(2026, 1, 10, 20, 0, tzinfo=madrid))["x"] == 10.0
    assert (
        len(
            series.filas_entre(
                df, datetime(2026, 1, 10, 19, tzinfo=canarias), datetime(2026, 1, 10, 20, tzinfo=canarias)
            )
        )
        == 2
    )
