"""Pipeline completo con respuestas reales de las APIs guardadas en tests/fixtures
(Open-Meteo, Commons y Overpass): sin red, y comprobando que el JSON publicado es válido."""
import json
import math
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

import condiciones as C
import descubrir_spots as D
import notificar as N
from comun import escribir_json, id_spot, limpiar_json

FIX = Path(__file__).parent / "fixtures"
LP = {"zona": "3b", "sqm": 21.38, "bortle": 4, "descripcion": "rural con algo de resplandor"}


class Respuesta:
    def __init__(self, datos):
        self.datos, self.status_code, self.headers = datos, 200, {}

    def raise_for_status(self):
        pass

    def json(self):
        return self.datos


@pytest.fixture(autouse=True)
def sin_red(monkeypatch, tmp_path):
    """Ninguna prueba sale a internet: caché vacía y contaminación lumínica fija."""
    monkeypatch.setattr(C, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(D, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(C, "contaminacion", lambda lat, lon: LP)
    monkeypatch.setattr(D, "contaminacion", lambda lat, lon: LP)
    monkeypatch.setattr(C.requests, "get", lambda *a, **k: pytest.fail("petición de red inesperada"))


def _sin_nan(obj):
    if isinstance(obj, float):
        assert math.isfinite(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _sin_nan(v)
    elif isinstance(obj, list):
        for v in obj:
            _sin_nan(v)


def _previsiones():
    datos = json.loads((FIX / "openmeteo.json").read_text())
    out = []
    for d in datos:
        df = pd.DataFrame(d["hourly"])
        df["time"] = pd.to_datetime(df["time"])
        out.append({"elevacion": d.get("elevation"), "horas": df.set_index("time")})
    return out


def _spots():
    return [
        {"id": id_spot("Puerto de Navacerrada", 40.793, -4.011), "nombre": "Puerto de Navacerrada",
         "lat": 40.793, "lon": -4.011, "tipo": "mirador", "origen": "propio", "contaminacion": None},
        {"id": id_spot("Faro de Fisterra", 42.8823, -9.2718), "nombre": "Faro de Fisterra",
         "lat": 42.8823, "lon": -9.2718, "tipo": "faro", "origen": "propio", "contaminacion": None},
    ]


def _fecha_inicial():
    return date.fromisoformat(json.loads((FIX / "openmeteo.json").read_text())[0]["hourly"]["time"][0][:10])


def test_informe_con_respuesta_guardada(tmp_path, monkeypatch):
    spots = _spots()
    # El orden de coordenadas que pide evaluar() debe coincidir con el de la respuesta guardada:
    # spot1, hz amanecer1, hz atardecer1, spot2, hz amanecer2, hz atardecer2
    prev = _previsiones()
    informe = C.evaluar(spots, 3, "Europe/Madrid", hoy=_fecha_inicial(), previsiones=prev)
    assert [s["nombre"] for s in informe["spots"]] == ["Puerto de Navacerrada", "Faro de Fisterra"]
    for s in informe["spots"]:
        assert len(s["dias"]) == 3
        assert s["contaminacion"] == LP
        for d in s["dias"]:
            assert set(d["notas"]) == {"amanecer", "atardecer", "astro", "niebla"}
            for n in d["notas"].values():
                assert 0 <= n["nota"] <= 10
                assert n["desglose"] and all("texto" in f and "puntos" in f for f in n["desglose"])
            assert d["sol"]["amanecer"] < d["sol"]["atardecer"]
            assert 60 < d["sol"]["az_amanecer"] < 130 and 230 < d["sol"]["az_atardecer"] < 300
            assert d["fiabilidad"] in ("alta", "media", "baja")
    assert informe["spots"][0]["dias"][0]["fiabilidad"] == "alta"
    assert informe["spots"][0]["dias"][2]["fiabilidad"] == "media"

    ruta = tmp_path / "informe.json"
    escribir_json(ruta, informe)
    texto = ruta.read_text()
    assert "NaN" not in texto and "Infinity" not in texto
    _sin_nan(json.loads(texto))


def test_peticion_open_meteo_simulada(monkeypatch):
    """pedir_tiempo() con la respuesta guardada servida como si viniera de la API."""
    monkeypatch.setattr(C.requests, "get", lambda *a, **k: Respuesta(json.loads((FIX / "openmeteo.json").read_text())))
    prev = C.pedir_tiempo([(40.793, -4.011)] * 6, 3, "Europe/Madrid")
    assert len(prev) == 6 and prev[0]["elevacion"] > 1500
    assert not prev[0]["horas"].empty


def test_limpiar_json_quita_nan():
    import numpy as np
    assert limpiar_json({"a": float("nan"), "b": [np.float64(1.5), np.int64(2)], "c": float("inf")}) == \
        {"a": None, "b": [1.5, 2], "c": None}


def test_id_spot_estable_y_legible():
    a = id_spot("Mirador de la Barranca", 40.7712, -4.0012)
    assert a == id_spot("Mirador de la Barranca", 40.77121, -4.00119)
    assert a.startswith("mirador-de-la-barranca-")
    assert id_spot("Peñalara", 40.85, -3.95).startswith("penalara-")


def test_cargar_mis_spots_ignora_comentarios(tmp_path):
    csv = tmp_path / "mis.csv"
    csv.write_text("nombre,lat,lon,tipo\n# comentario\nMi sitio,40.5,-3.9,embalse\n")
    spots = C.cargar_spots(None, csv)
    assert len(spots) == 1 and spots[0]["tipo"] == "embalse" and spots[0]["origen"] == "propio"


# ------------------------------------------------------------ descubrir ----
def _commons_guardado(params):
    if params.get("list") == "geosearch":
        return json.loads((FIX / "commons_geosearch.json").read_text())
    datos = json.loads((FIX / "commons_detalles.json").read_text())
    pedidos = set(map(int, params["pageids"].split("|")))
    datos = json.loads(json.dumps(datos))
    datos["query"]["pages"] = [p for p in datos["query"]["pages"] if p["pageid"] in pedidos]
    return datos


def test_descubrir_con_respuestas_guardadas(monkeypatch, tmp_path):
    monkeypatch.setattr(D, "_commons", _commons_guardado)
    monkeypatch.setattr(D, "_cache_get", lambda clave: json.loads((FIX / "overpass.json").read_text())
                        if clave.startswith("[out:json]") else None)
    bbox = (-3.92, 40.74, -3.86, 40.78)
    fotos = D.buscar_commons(bbox)
    assert not fotos.empty
    assert fotos.licencia.notna().all()
    fotos = D.agrupar(fotos, radio_m=400, min_fotos=3, min_autores=2)
    osm = D.buscar_osm(bbox)
    assert not osm.empty and osm.nombre.notna().any()
    spots = D.resumir_spots(fotos, osm, D.ZoneInfo("Europe/Madrid"))
    D.guardar(spots, tmp_path, "La Pedriza")
    geo = json.loads((tmp_path / "spots.geojson").read_text())
    _sin_nan(geo)
    for f in geo["features"]:
        p = f["properties"]
        assert p["id"] and p["nombre"]
        assert len(p["meses"]) == 12
        for foto in p["galeria"]:
            assert foto["autor"] and foto["licencia"] and foto["url"].startswith("https://")


def test_clasificar_paisaje():
    assert D.clasificar_paisaje(["Landscapes of Madrid", "Quality images"]) == (True, True)
    assert not D.clasificar_paisaje(["Quality images of Segovia", "Throne room of the Alcázar of Segovia"])[0]
    assert D.clasificar_paisaje(["Sierra de Guadarrama"])[0]
    assert not D.clasificar_paisaje(["Interiors of churches", "Sierra"])[0]
    assert not D.clasificar_paisaje(["Birds of Spain"])[0]
    assert not D.clasificar_paisaje(["Buildings in Madrid"])[0]


# ------------------------------------------------------------ notificar ----
def test_notificar_lee_el_informe_nuevo():
    informe = C.evaluar(_spots(), 2, "Europe/Madrid", hoy=_fecha_inicial(), previsiones=_previsiones())
    fecha = informe["fechas"][0]
    msg = N.construir_mensaje(informe, fecha, umbral=0, top=3, web="https://ejemplo.app")
    assert msg and "/10" in msg and "https://ejemplo.app/spot/" in msg
    assert N.construir_mensaje(informe, "1999-01-01", 0, 3) is None


# ------------------------------------------------- calidad de spots y nombres ----
def test_paisaje_por_inicio_de_palabra():
    """'río' no debe casar con 'Riofrío' (un pueblo), ni las fotos de la ISS pasar por paisaje."""
    assert not D.clasificar_paisaje(["Navas de Riofrío"])[0]
    assert D.clasificar_paisaje(["Río Lozoya"])[0]
    assert not D.clasificar_paisaje(["Daytime Earth viewed from space", "Clouds"])[0]
    assert not D.clasificar_paisaje(["Quality images of churches in Castile and León"])[0]
    assert not D.clasificar_paisaje(["Views of the Cathedral of Segovia from Plaza Mayor"])[0]
    assert D.clasificar_paisaje(["Views of the Alcázar of Segovia from the Eresma Valley"])[0]
    # pueblos con "Monte" en el nombre no son montañas; estaciones y naves tampoco son paisaje
    assert not D.clasificar_paisaje(["Ortigosa del Monte train station"])[0]
    assert not D.clasificar_paisaje(["Cabanillas del Monte shearing shed"])[0]
    # gallego y costa
    assert D.clasificar_paisaje(["Fervenza do Ézaro"])[0]
    assert D.clasificar_paisaje(["Praia de Niñóns"])[0]
    assert D.clasificar_paisaje(["Cabo Finisterre"])[0]


@pytest.mark.parametrize("titulo,esperado", [
    ("EMBALSE DE SANTILLANA (6495112213)", "Embalse de Santillana"),
    ("Puente de Navalacarreta (2 de mayo de 2015, Boca del Asno, Segovia) 09", "Puente de Navalacarreta"),
    ("2011-06-05 Cascada del Purgatorio - panoramio", "Cascada del Purgatorio"),
    ("Pico de la Miel - 01", "Pico de la Miel"),
    ("Embalse del río Pirón2", "Embalse del río Pirón"),
    ("LaSierra9", "La Sierra"),
])
def test_limpiar_nombre(titulo, esperado):
    assert D.limpiar_nombre(titulo) == esperado


@pytest.mark.parametrize("cat,esperado", [
    ("Puentes Viejas Reservoir", "Embalse de Puentes Viejas"),
    ("Views of Monastery of El Paular", "Monasterio de El Paular"),
    ("Manzanares River in La Pedriza", "Río Manzanares en La Pedriza"),
    ("Laguna Grande de Peñalara", "Laguna Grande de Peñalara"),
])
def test_traducir_categoria(cat, esperado):
    assert D.traducir_categoria(cat) == esperado


def test_categoria_nombre_ignora_genericas():
    cats = pd.Series([["Quality images of the Community of Madrid", "Laguna Grande de Peñalara"],
                      ["Laguna Grande de Peñalara", "Snow at Sierra de Guadarrama"],
                      ["Laguna Grande de Peñalara", "2012 in Segovia"]])
    assert D.categoria_nombre(cats, 3) == "Laguna Grande de Peñalara"


def test_miradores_sin_nombre():
    osm = pd.DataFrame([
        {"osm_id": "node/1", "lat": 40.80, "lon": -3.90, "nombre": None, "tipo": "viewpoint", "ele": None, "direction": None},
        {"osm_id": "node/2", "lat": 40.805, "lon": -3.90, "nombre": "Pico Pequeño", "tipo": "peak", "ele": None, "direction": None},
        {"osm_id": "node/3", "lat": 41.50, "lon": -3.00, "nombre": None, "tipo": "viewpoint", "ele": None, "direction": None},
    ])
    out = D.nombrar_miradores(osm[osm.tipo == "viewpoint"], osm)
    assert list(out.nombre) == ["Mirador junto a Pico Pequeño"]   # el aislado y sin nombre se descarta
