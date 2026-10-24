"""Casos sintéticos extremos: cada factor físico mueve la nota en el sentido correcto."""
import pytest

from puntuacion import capa_nubosa, nota_astro, nota_luz, nota_niebla, prob_niebla_radiacion


# ================================================================== luz ====
def cielo(low=0, mid=0, high=0, lluvia=0, mm=0.0, vis=24000, viento=10, hum=60):
    return {"cloud_cover_low": low, "cloud_cover_mid": mid, "cloud_cover_high": high,
            "precipitation_probability": lluvia, "precipitation": mm, "visibility": vis,
            "wind_speed_10m": viento, "relative_humidity_2m": hum}


def camino(bajas=(0, 0, 0, 0), medias=(0, 0, 0, 0), altas=(0, 0, 0, 0)):
    return [{"km": km, "low": b, "mid": m, "high": h}
            for km, b, m, h in zip((15, 40, 80, 150), bajas, medias, altas)]


def luz(local=None, cam=None, **aire):
    return nota_luz(local or cielo(), cam if cam is not None else camino(), aire or None)


def test_lienzo_ideal_con_camino_libre_es_excelente():
    assert luz(cielo(high=50), camino(altas=(50, 40, 0, 0))).valor >= 8.5


def test_cielo_despejado_es_correcto_pero_plano():
    assert 2.5 <= luz().valor <= 4


def test_todo_cubierto_de_nubes_bajas_es_malo():
    assert luz(cielo(low=100, mid=100), camino(bajas=(100, 100, 100, 100))).valor <= 1


def test_banco_de_nubes_bajas_hacia_el_sol_apaga_el_cielo():
    """Un banco a 30-50 km basta para que no se encienda nada (Stephen Bay)."""
    libre = luz(cielo(high=50), camino()).valor
    banco = luz(cielo(high=50), camino(bajas=(0, 100, 0, 0))).valor
    assert banco <= libre - 4


def test_el_banco_lejano_pesa_menos_que_el_cercano():
    cerca = luz(cielo(high=50), camino(bajas=(0, 100, 0, 0))).valor
    lejos = luz(cielo(high=50), camino(bajas=(0, 0, 0, 100))).valor
    assert lejos > cerca


def test_capa_alta_completa_con_luz_por_debajo_sigue_siendo_buena():
    """'Bañado en rojo' (NOAA): capa media/alta continua y horizonte libre."""
    assert luz(cielo(high=100), camino(altas=(100, 100, 100, 100))).valor >= 6


def test_nubes_bajas_sobre_el_spot_tapan_el_lienzo():
    assert luz(cielo(low=90, high=50), camino()).valor < luz(cielo(high=50), camino()).valor - 3


def test_lluvia_resta():
    assert luz(cielo(high=50, lluvia=90, mm=2)).valor <= luz(cielo(high=50)).valor - 4


def test_calima_apaga_el_color_y_el_aire_lavado_lo_aviva():
    normal = luz(cielo(high=50), aod=0.2).valor
    assert luz(cielo(high=50), aod=0.7, polvo=150).valor < normal - 2
    assert luz(cielo(high=50), aod=0.2, lluvia_previa_mm=6).valor >= normal


def test_humedad_alta_resta_un_poco():
    assert luz(cielo(high=50, hum=98)).valor < luz(cielo(high=50, hum=60)).valor


def test_reflejos_solo_en_agua_y_sin_viento():
    agua = nota_luz(cielo(high=50, viento=2), camino(), es_agua=True)
    tierra = nota_luz(cielo(high=50, viento=2), camino(), es_agua=False)
    assert "reflejos" in agua.avisos and "reflejos" not in tierra.avisos


@pytest.mark.parametrize("local,cam", [
    (cielo(low=50, high=60, lluvia=40, vis=3000, hum=95), camino(bajas=(30, 70, 20, 0))),
    (cielo(high=100), camino()),
    (cielo(), camino()),
])
def test_desglose_suma_la_nota(local, cam):
    d = nota_luz(local, cam, {"aod": 0.3}).a_dict()
    total = sum(f["puntos"] for f in d["desglose"])
    assert abs(max(0, min(10, total)) - d["nota"]) < 0.35
    assert all(f["texto"] for f in d["desglose"])


def test_valores_ausentes_no_rompen():
    assert 0 <= nota_luz({"cloud_cover_low": float("nan")}, []).valor <= 10


# =============================================================== noche ====
def noche(nubes=0, luna=0.0, n=8):
    return [{"t": f"{(21 + i) % 24:02d}:00", "nubes": nubes(i) if callable(nubes) else nubes,
             "luna": luna(i) if callable(luna) else luna} for i in range(n)]


def astro(horas=None, **k):
    base = dict(sqm=21.8, zona_lp="1b", vapor_mm=8, aod=0.05, humedad=60)
    base.update(k)
    return nota_astro(horas if horas is not None else noche(), **base)


def test_noche_perfecta():
    assert astro().valor >= 9.5


def test_luna_llena_toda_la_noche_hunde_la_nota():
    assert astro(noche(luna=1.0)).valor <= 4


def test_luna_que_se_pone_pronto_no_importa():
    """Basta una ventana oscura de 3 h: la luna que se pone a medianoche no estropea la noche."""
    assert astro(noche(luna=lambda i: 0.6 if i < 3 else 0.0)).valor >= 9


def test_una_ventana_despejada_en_noche_nublada_vale():
    """Lo que importa es tener 3 h buenas, no la media de toda la noche."""
    assert astro(noche(nubes=lambda i: 100 if i < 5 else 0)).valor >= 8.5
    assert astro(noche(nubes=100)).valor <= 1


def test_contaminacion_luminica_resta():
    assert astro(sqm=18.0, zona_lp="7b").valor <= 3
    assert astro(sqm=20.7, zona_lp="4b").valor < astro(sqm=21.8).valor


def test_bortle_4_despejado_merece_la_pena():
    assert astro(sqm=21.1, zona_lp="3b").valor >= 8


def test_cupula_de_luz_hacia_donde_se_mira_resta():
    assert astro(cupula={"zona": "7a", "km": 35, "hacia": "el sur"}).valor < astro().valor - 1.5


def test_transparencia():
    assert astro(vapor_mm=35, aod=0.5, humedad=95).valor < astro().valor - 3


def test_rachas_fuertes_restan():
    assert astro(rachas=70).valor < astro(rachas=20).valor - 2


def test_rocio_avisa_y_via_lactea_suma():
    assert "rocio" in astro(margen_rocio=1).avisos
    assert astro(sqm=20.7, vl_horas_sin_luna=3, vl_altura_max=20).valor > astro(sqm=20.7).valor


def test_sin_noche_astronomica():
    assert nota_astro([], 21.8).valor == 0


def test_desglose_astro_suma_la_nota():
    d = astro(noche(nubes=40, luna=0.3), sqm=20.3, cupula={"zona": "6a", "km": 20}, rachas=45).a_dict()
    assert abs(sum(f["puntos"] for f in d["desglose"]) - d["nota"]) < 0.35


# ============================================================== niebla ====
def hora(rh, t, td, viento, vis=24000, low=0, lluvia=0, nubes=0):
    return {"relative_humidity_2m": rh, "temperature_2m": t, "dew_point_2m": td,
            "wind_speed_10m": viento, "visibility": vis, "cloud_cover_low": low,
            "precipitation_probability": lluvia, "cloud_cover": nubes}


def test_niebla_en_embalse_con_aire_saturado_y_calma():
    assert nota_niebla([hora(100, 3, 3, 3)], 900, tipo="embalse").valor >= 8.5


def test_niebla_dentro_de_un_mirador_es_mala():
    m = nota_niebla([hora(100, 5, 5, 3, vis=300)], 1400, tipo="mirador")
    e = nota_niebla([hora(100, 5, 5, 3, vis=300)], 1400, tipo="embalse")
    assert m.valor <= 4 < e.valor


def test_aire_seco_sin_niebla():
    assert nota_niebla([hora(55, 12, 2, 3)]).valor == 0


def test_viento_disipa_la_niebla():
    assert nota_niebla([hora(99, 5, 4.8, 22)]).valor < nota_niebla([hora(99, 5, 4.8, 4)]).valor


def test_probabilidad_calibrada_y_monotona():
    """Calibración con METAR: ni con aire saturado la niebla es segura (~50 %)."""
    from puntuacion import prob_niebla_radiacion
    ps = [prob_niebla_radiacion([hora(rh, 5, 4, 4)])[0] for rh in (80, 88, 92, 96, 100)]
    assert ps == sorted(ps) and ps[0] < 0.01 and 0.4 <= ps[-1] <= 0.55
    assert prob_niebla_radiacion([hora(90, 5, 4, 4, vis=400)])[0] >= 0.6   # el modelo ya la ve


def test_lluvia_resta_a_la_niebla():
    assert nota_niebla([hora(99, 5, 4.8, 3, lluvia=90)], tipo="embalse").valor < \
        nota_niebla([hora(99, 5, 4.8, 3)], tipo="embalse").valor


PERFIL_INVERSION = {"niveles": [
    {"hpa": 950, "z": 650, "t": 4, "hr": 100, "nubes": 95},
    {"hpa": 925, "z": 850, "t": 3, "hr": 99, "nubes": 90},
    {"hpa": 900, "z": 1080, "t": 7, "hr": 45, "nubes": 0},
    {"hpa": 850, "z": 1520, "t": 6, "hr": 30, "nubes": 0},
]}


def test_capa_nubosa_con_inversion():
    c = capa_nubosa(PERFIL_INVERSION)
    assert 850 < c["techo"] < 1080 and c["cobertura"] >= 90 and c["inversion"] >= 3


def test_mar_de_nubes_desde_una_cumbre():
    capa = capa_nubosa(PERFIL_INVERSION)
    seco = [hora(70, 5, -2, 6)]
    n = nota_niebla(seco, 1800, capa, tipo="cumbre")
    assert "mar_de_nubes" in n.avisos and n.valor >= 9
    debajo = nota_niebla(seco, 700, capa, tipo="mirador")
    assert "mar_de_nubes" not in debajo.avisos
    dentro = nota_niebla([hora(100, 3, 3, 3, vis=200, low=100)], 1800, capa, tipo="cumbre", bajas_spot=100)
    assert "mar_de_nubes" not in dentro.avisos
    poca = capa_nubosa({"niveles": [{"hpa": 925, "z": 850, "t": 3, "hr": 90, "nubes": 45},
                                    {"hpa": 900, "z": 1080, "t": 7, "hr": 40, "nubes": 0}]})
    assert "mar_de_nubes" not in nota_niebla(seco, 1800, poca, tipo="cumbre").avisos


def test_sin_capa_baja():
    assert capa_nubosa({"niveles": [{"hpa": 900, "z": 1000, "t": 5, "hr": 50, "nubes": 0}]}) is None


def test_calima_extrema_del_15_de_marzo_de_2022():
    """ERA5 vio el polvo como 100 % de nubes altas; con 168 µg/m³ el sol apenas se veía."""
    local = cielo(mid=30, high=100, hum=40)
    cam = camino(altas=(100, 100, 100, 100))
    assert luz(local, cam, polvo=168).valor <= 3.2
    assert luz(local, cam).valor >= 6.5


# ========================================================= relieve y luna ====
def test_montana_hacia_el_sol_resta():
    libre = nota_luz(cielo(high=50), camino(), relieve=0.5).valor
    valle = nota_luz(cielo(high=50), camino(), relieve=9, hora_relieve="18:40")
    assert valle.valor < libre - 1.5
    assert any("18:40" in t for t, _ in valle.factores)


def test_luna_llena_saliendo_al_atardecer_es_excelente():
    from puntuacion import nota_luna
    e = {"tipo": "salida", "hora": "18:11", "iluminacion": 1.0, "altura_sol": 1.0, "horizonte": 0.5, "azimut": 73}
    assert nota_luna(e, {"cloud_cover": 5}, camino()).valor >= 9
    assert nota_luna({**e, "iluminacion": 0.45}).valor < 7          # luna poco llena
    assert nota_luna({**e, "altura_sol": -11}).valor < 7             # ya es de noche: paisaje negro
    assert nota_luna(e, {"cloud_cover": 95}).valor < 3               # cubierto
    assert nota_luna(e, None, camino(bajas=(0, 100, 0, 0))).valor < 6  # banco de nubes hacia la luna
    assert nota_luna(None).valor == 0


def test_visibilidad_baja_sin_humedad_no_es_niebla():
    """Lagos de Cabdella (24-oct-2026): el modelo daba 0,3 km de visibilidad con un 71 % de humedad."""
    seco = [{"relative_humidity_2m": 71, "wind_speed_10m": 9, "visibility": 300}]
    humedo = [{"relative_humidity_2m": 95, "wind_speed_10m": 9, "visibility": 300}]
    assert prob_niebla_radiacion(seco)[0] < 0.1
    assert prob_niebla_radiacion(humedo)[0] >= 0.6
