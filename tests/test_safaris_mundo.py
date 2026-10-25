"""Safaris en todo el mundo: cribado, cómo llegar, clima y OSM con datos reales grabados (Kruger)."""

import json

from conftest import FIX

from rasante.safaris import mundo, practico
from rasante.safaris.mundo_cli import indice, puntuacion, quitar_duplicados


def test_radio_y_caja():
    assert mundo.radio_km(19_623e6, "parque nacional") == 79.0  # Kruger: ~79 km de radio
    assert mundo.radio_km(1e6, "reserva de caza") == mundo.RADIO_MIN_KM
    assert mundo.radio_km(None, "parque nacional") == 15.0
    c = mundo.caja(-24.0, 31.5, 111)
    assert c["decimalLatitude"] == "-25.0000,-23.0000"


def test_slug():
    assert mundo.slug("Parque Nacional Kruger") == "parque-nacional-kruger"
    assert mundo.slug("Hluhluwe–iMfolozi") == "hluhluwe-imfolozi"


def test_llegar_a_kruger():
    a = practico.Aeropuertos((FIX / "ourairports_kruger.csv").read_text())
    ll = a.llegar(-24.0, 31.5, 79)
    iatas = [x["iata"] for x in ll["aeropuertos"]]
    assert iatas[0] == "PHW"  # Phalaborwa, el regular más cercano
    assert any(x["internacional"] for x in ll["aeropuertos"])  # y el gran aeropuerto internacional más cercano
    nombres = [p["nombre"] for p in ll["pistas"]]
    assert "Letaba Rest Camp Airstrip" in nombres and "Mossel Bay Airport" not in nombres


def test_clima_de_la_nasa(monkeypatch):
    grabado = json.loads((FIX / "power_kruger.json").read_text())
    monkeypatch.setattr(practico.CACHE, "leer", lambda clave: grabado)
    c = practico.clima(-24.0, 31.5)
    assert len(c["lluvia_mm"]) == 12
    assert c["lluvia_mm"][0] > 50 > c["lluvia_mm"][6]  # verano austral lluvioso, invierno seco
    assert practico.meses_secos(c) == [i + 1 for i, v in enumerate(c["lluvia_mm"]) if v < 50]
    assert 7 in practico.meses_secos(c)


def test_osm_se_clasifica():
    datos = {
        "elements": [
            {"type": "node", "id": 1, "lat": -24.0, "lon": 31.6, "tags": {"tourism": "camp_site", "name": "Satara"}},
            {"type": "node", "id": 2, "lat": -24.1, "lon": 31.5, "tags": {"tourism": "camp_site", "name": "4R1"}},
            {
                "type": "node",
                "id": 3,
                "lat": -24.3,
                "lon": 31.2,
                "tags": {"office": "travel_agent", "name": "Safaris SA", "website": "https://x"},
            },
            {"type": "node", "id": 4, "lat": -24.4, "lon": 31.7, "tags": {"barrier": "gate", "name": "Orpen Gate"}},
            {"type": "node", "id": 5, "lat": -24.6, "lon": 31.0, "tags": {"place": "town", "name": "Hoedspruit"}},
        ]
    }
    o = practico.clasificar(datos, -24.0, 31.5)
    assert [a["nombre"] for a in o["alojamientos"]] == ["Satara"]  # fuera el código de acampada
    assert o["operadores"][0]["web"] == "https://x"
    assert o["puertas"][0]["nombre"] == "Orpen Gate" and o["pueblos"][0]["nombre"] == "Hoedspruit"


def test_duplicados_e_indice():
    base = {"lat": -24.0, "lon": 31.5, "estrella": {}, "meses_secos": [], "destacado": False, "foto": None}
    ps = [
        {**base, "id": "a", "nombre": "Kruger", "puntuacion": 10, "pais": "Q258", "radio_km": 79, "n_mamiferos": 90},
        {**base, "id": "b", "nombre": "Kruger", "puntuacion": 5, "pais": "Q258", "radio_km": 20, "n_mamiferos": 50},
        {
            **base,
            "id": "c",
            "nombre": "Kruger",
            "puntuacion": 4,
            "pais": "Q258",
            "radio_km": 20,
            "n_mamiferos": 40,
            "lat": 0,
        },
    ]
    sin = quitar_duplicados(ps)
    assert [p["id"] for p in sin] == ["a", "c"]  # el de la misma zona sobra; uno lejos con el mismo nombre, no
    filas = indice({"parques": sin, "paises": {"Q258": {"nombre": "Sudáfrica", "continente": "África"}}})
    assert filas[0]["p"] == "Sudáfrica" and filas[0]["c"] == "África"
    assert puntuacion(90, 1000) > puntuacion(50, 1000)
    assert puntuacion(40, 1000, n_estrella=8) > puntuacion(200, 50000, n_estrella=1)  # el safari, no los murciélagos
