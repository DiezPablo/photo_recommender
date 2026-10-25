"""Logística de OpenStreetMap: qué cuenta, áreas en su centro y los más cercanos a cada lugar."""

from conftest import FIX

from rasante.logistica.cercanos import Indice, km
from rasante.logistica.cli import calcular
from rasante.logistica.osm import clasificar, leer_puntos


def test_clasificar():
    assert clasificar({"amenity": "parking"}) == ("aparcamiento", None)
    assert clasificar({"amenity": "parking", "access": "private"}) is None
    assert clasificar({"amenity": "parking", "parking": "underground"}) is None
    assert clasificar({"tourism": "wilderness_hut"}) == ("refugio", "refugio libre")
    assert clasificar({"amenity": "shelter", "shelter_type": "picnic_shelter"}) is None
    assert clasificar({"natural": "spring"}) is None  # un manantial no es agua potable
    assert clasificar({"natural": "spring", "drinking_water": "yes"}) == ("fuente", "manantial")


def test_leer_puntos_de_osm():
    puntos = leer_puntos(FIX / "logistica.osm")
    tipos = sorted(p["tipo"] for p in puntos)
    assert tipos == ["aparcamiento", "aparcamiento", "camping", "fuente", "fuente", "refugio"]
    camping = next(p for p in puntos if p["tipo"] == "camping")
    assert camping["nombre"] == "Camping El Valle" and camping["osm"] == "way/100"
    assert abs(camping["lat"] - 40.7908) < 0.001  # centro del área


def test_los_mas_cercanos():
    puntos = leer_puntos(FIX / "logistica.osm")
    cerca = Indice(puntos).cerca(40.801, -3.951)
    por_tipo = {}
    for c in cerca:
        por_tipo.setdefault(c["tipo"], []).append(c)
    assert por_tipo["aparcamiento"][0]["nombre"] == "Aparcamiento de Cotos"
    assert len(por_tipo["aparcamiento"]) == 1  # el de Navarra queda lejos
    assert [f["km"] for f in por_tipo["fuente"]] == sorted(f["km"] for f in por_tipo["fuente"])
    assert por_tipo["refugio"][0]["nombre"] == "Refugio Zabala"
    assert 4 < km((40.8, -3.95), (40.84, -3.94)) < 5  # ~4,5 km: dentro de los 6 km de los refugios


def test_calcular_spots_y_rutas():
    puntos = leer_puntos(FIX / "logistica.osm")
    datos = calcular(
        puntos,
        [{"id": "a", "lat": 40.801, "lon": -3.951}, {"id": "lejos", "lat": 37, "lon": -6}],
        [{"id": "r", "inicio": [40.79, -3.91]}],
    )
    assert "a" in datos["spots"] and "lejos" not in datos["spots"]
    assert any(c["tipo"] == "camping" for c in datos["rutas"]["r"])
    assert all("detalle" not in c or c["detalle"] for c in datos["spots"]["a"])
