"""Verificación con METAR: lectura de los partes, criterios por día y marcador frente a la persistencia."""

from datetime import date

import pandas as pd

from rasante.verificacion import marcador, observado, previsto

CSV = """station,valid,wxcodes,vsby,skyc1,skyc2,skyc3,skyc4
LEMD,2026-01-10 05:00,FG,0.12,VV,,,
LEMD,2026-01-10 05:30,BR,0.5,FEW,,,
LEMD,2026-01-10 16:30,,6.21,BKN,,,
LEMD,2026-01-10 17:00,,6.21,OVC,,,
LEMD,2026-01-10 17:30,,6.21,BKN,,,
LEMD,2026-01-10 20:00,,6.21,,,,
LEMD,2026-01-10 21:00,,6.21,,,,
LEMD,2026-01-10 22:00,,6.21,FEW,,,
LEMD,2026-01-10 23:00,,6.21,SCT,,,
LEMD,2026-01-11 00:00,,6.21,BKN,,,
LEMD,2026-01-11 01:00,,6.21,,,,
"""


def test_observado_niebla_atardecer_y_noche():
    df = observado.leer(CSV)
    r = observado.resumir(df, 40.472, -3.561, date(2026, 1, 10))
    assert r["niebla"] is True  # FG y visibilidad < 1 km de madrugada
    assert r["cubierto"] is True  # BKN/OVC en torno a la puesta (17:00 UTC en enero)
    assert r["despejadas"] == 4  # 20-23 h sin BKN/OVC; a las 00 h se tapa


def test_previsto_con_los_mismos_criterios():
    horas = pd.date_range("2026-01-10 00:00", "2026-01-11 12:00", freq="h", tz="UTC")
    df = pd.DataFrame(
        {
            "cloud_cover_low": [0.0] * len(horas),
            "cloud_cover_mid": [90.0 if 16 <= t.hour <= 18 and t.day == 10 else 0.0 for t in horas],
            "relative_humidity_2m": [100.0 if t.hour < 9 else 60.0 for t in horas],
            "wind_speed_10m": [2.0] * len(horas),
            "visibility": [24000.0] * len(horas),
        },
        index=horas,
    )
    r = previsto.resumir(df, 40.472, -3.561, date(2026, 1, 10))
    assert r["niebla"] >= 0.4
    assert r["cubierto"] is True and r["tapado"] == 90
    assert r["despejadas"] >= 6


def test_marcador_frente_a_persistencia():
    obs = [
        {
            "oaci": "LEMD",
            "fecha": f"2026-01-{d:02d}",
            "niebla": d % 2 == 0,
            "cubierto": d % 2 == 0,
            "despejadas": 0 if d % 2 else 5,
        }
        for d in range(1, 11)
    ]
    # previsión perfecta emitida el día anterior; la persistencia falla siempre (alterna)
    prev = [
        {
            "emitida": f"2026-01-{d - 1:02d}",
            "oaci": "LEMD",
            "fecha": o["fecha"],
            "niebla": 0.6 if o["niebla"] else 0.0,
            "tapado": 90 if o["cubierto"] else 0,
            "cubierto": o["cubierto"],
            "despejadas": o["despejadas"],
        }
        for d, o in zip(range(1, 11), obs, strict=True)
        if d > 1
    ]
    h = marcador.fusionar({}, prev, obs, date(2026, 1, 11))
    m = marcador.marcador(h, date(2026, 1, 11))
    assert m["casos"] == 9
    assert m["niebla"]["detectadas"] == m["niebla"]["observadas"] == 5
    assert m["niebla"]["avisos_acertados"] == m["niebla"]["avisos"]
    assert m["atardecer_cubierto"] == {"acierto": 100, "persistencia": 0}
    assert m["noche_despejada"]["acierto"] == 100


def test_fusionar_recorta_y_no_duplica():
    viejo = {"previsiones": [{"emitida": "2025-01-01", "oaci": "LEMD", "fecha": "2025-01-02"}], "observaciones": []}
    nuevo = [{"emitida": "2026-01-10", "oaci": "LEMD", "fecha": "2026-01-11"}] * 2
    h = marcador.fusionar(viejo, nuevo, [], date(2026, 1, 11))
    assert len(h["previsiones"]) == 1 and h["previsiones"][0]["fecha"] == "2026-01-11"
