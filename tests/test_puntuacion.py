"""Casos sintéticos extremos: la nota debe moverse en el sentido correcto."""
from puntuacion import nota_astro, nota_luz, nota_niebla


def cielo(low=0, mid=0, high=0, lluvia=0, vis=24000, viento=10, **extra):
    return {"cloud_cover_low": low, "cloud_cover_mid": mid, "cloud_cover_high": high,
            "precipitation_probability": lluvia, "visibility": vis, "wind_speed_10m": viento, **extra}


# ---------------------------------------------------------------- luz ----
def test_lienzo_ideal_es_lo_mejor():
    ideal = nota_luz(cielo(high=50), cielo()).valor
    despejado = nota_luz(cielo(), cielo()).valor
    cubierto_alto = nota_luz(cielo(high=100), cielo()).valor
    assert ideal >= 8
    assert despejado < ideal and cubierto_alto < ideal
    assert 2 <= despejado <= 5          # se puede salir, pero cielo plano


def test_cubierto_de_nubes_bajas_es_malo():
    assert nota_luz(cielo(low=100, mid=100), cielo(low=100)).valor <= 1.5


def test_horizonte_tapado_resta():
    libre = nota_luz(cielo(high=50), cielo(low=0)).valor
    tapado = nota_luz(cielo(high=50), cielo(low=100)).valor
    assert tapado <= libre - 3


def test_lluvia_resta():
    seco = nota_luz(cielo(high=50), cielo()).valor
    lluvia = nota_luz(cielo(high=50, lluvia=100), cielo()).valor
    assert lluvia <= seco - 2.5


def test_niebla_densa_resta_a_la_luz():
    assert nota_luz(cielo(high=50, vis=500), cielo()).valor < nota_luz(cielo(high=50), cielo()).valor


def test_reflejos_solo_en_agua_y_sin_viento():
    agua = nota_luz(cielo(high=50, viento=2), cielo(), es_agua=True)
    tierra = nota_luz(cielo(high=50, viento=2), cielo(), es_agua=False)
    ventoso = nota_luz(cielo(high=50, viento=25), cielo(), es_agua=True)
    assert "reflejos" in agua.avisos and "reflejos" not in tierra.avisos + ventoso.avisos
    assert agua.valor >= tierra.valor


def test_desglose_suma_la_nota():
    d = nota_luz(cielo(low=50, high=60, lluvia=40, vis=8000), cielo(low=70)).a_dict()
    total = sum(f["puntos"] for f in d["desglose"])
    assert abs(max(0, min(10, total)) - d["nota"]) < 0.25
    assert all(isinstance(f["texto"], str) and f["texto"] for f in d["desglose"])


def test_valores_ausentes_no_rompen():
    n = nota_luz({"cloud_cover_low": float("nan")}, {})
    assert 0 <= n.valor <= 10


# --------------------------------------------------------------- astro ----
def astro(**k):
    base = dict(nubes=0, humedad=60, viento=5, rocio_margen=8, horas_sin_luna=9,
                horas_noche=9, luna_iluminacion=0.0, zona_lp="2a", vl_horas_sin_luna=0)
    base.update(k)
    return nota_astro(**base)


def test_noche_perfecta():
    assert astro().valor >= 9.5


def test_luna_llena_toda_la_noche_hunde_la_nota():
    llena = astro(luna_iluminacion=1.0, horas_sin_luna=0).valor
    assert llena <= 5
    assert llena < astro().valor


def test_luna_que_se_pone_pronto_apenas_resta():
    assert astro(luna_iluminacion=0.5, horas_sin_luna=6).valor >= 9.5


def test_nubes_hunden_la_nota():
    assert astro(nubes=100).valor <= 1.5
    assert astro(nubes=30).valor < astro(nubes=0).valor


def test_contaminacion_luminica_resta():
    assert astro(zona_lp="7b").valor <= 4
    assert astro(zona_lp="5a").valor < astro(zona_lp="2a").valor


def test_rocio_avisa():
    assert "rocio" in astro(rocio_margen=1).avisos
    assert "rocio" not in astro(rocio_margen=6).avisos


def test_via_lactea_suma():
    assert astro(nubes=20, vl_horas_sin_luna=3).valor > astro(nubes=20).valor


def test_sin_noche_astronomica():
    assert astro(horas_noche=0).valor == 0


# -------------------------------------------------------------- niebla ----
def hora(rh, t, td, viento, vis=24000, low=0, lluvia=0):
    return {"relative_humidity_2m": rh, "temperature_2m": t, "dew_point_2m": td,
            "wind_speed_10m": viento, "visibility": vis, "cloud_cover_low": low,
            "precipitation_probability": lluvia}


def test_niebla_densa_probable():
    assert nota_niebla([hora(99, 5, 4.8, 2, vis=300)]).valor >= 8


def test_aire_seco_sin_niebla():
    assert nota_niebla([hora(55, 12, 2, 3)]).valor == 0


def test_viento_disipa_la_niebla():
    assert nota_niebla([hora(98, 5, 4.5, 30)]).valor < nota_niebla([hora(98, 5, 4.5, 2)]).valor


def test_lluvia_resta_a_la_niebla():
    assert nota_niebla([hora(98, 5, 4.5, 2, lluvia=90)]).valor < nota_niebla([hora(98, 5, 4.5, 2)]).valor


def test_mar_de_nubes_en_cumbre():
    n = nota_niebla([hora(80, 3, -2, 5, low=10)], elevacion_spot=1900, bajas_alrededor=90)
    assert "mar_de_nubes" in n.avisos and n.valor >= 5
    llano = nota_niebla([hora(80, 3, -2, 5, low=10)], elevacion_spot=650, bajas_alrededor=90)
    assert "mar_de_nubes" not in llano.avisos
