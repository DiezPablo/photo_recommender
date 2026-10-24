"""Descubrimiento de spots: Commons (paisaje, galería), nombres y recuentos."""

import json

import numpy as np
import pytest
from conftest import FIX

from rasante.spots import commons
from rasante.spots.commons import clasificar_paisaje, galeria
from rasante.spots.nombres import limpiar_nombre
from rasante.spots.seleccion import entero


def test_clasificar_paisaje():
    assert clasificar_paisaje(["Landscapes of Madrid", "Quality images"]) == (True, True)
    assert not clasificar_paisaje(["Quality images of Segovia", "Throne room of the Alcázar of Segovia"])[0]
    assert clasificar_paisaje(["Sierra de Guadarrama"])[0]
    assert not clasificar_paisaje(["Interiors of churches", "Sierra"])[0]
    assert not clasificar_paisaje(["Birds of Spain"])[0]
    assert not clasificar_paisaje(["Buildings in Madrid"])[0]


def test_paisaje_por_inicio_de_palabra():
    """'río' no debe casar con 'Riofrío' (un pueblo), ni las fotos de la ISS pasar por paisaje."""
    assert not clasificar_paisaje(["Navas de Riofrío"])[0]
    assert clasificar_paisaje(["Río Lozoya"])[0]
    assert not clasificar_paisaje(["Daytime Earth viewed from space", "Clouds"])[0]
    assert not clasificar_paisaje(["Quality images of churches in Castile and León"])[0]
    assert not clasificar_paisaje(["Views of the Cathedral of Segovia from Plaza Mayor"])[0]
    assert clasificar_paisaje(["Views of the Alcázar of Segovia from the Eresma Valley"])[0]
    # pueblos con "Monte" en el nombre no son montañas; estaciones y naves tampoco son paisaje
    assert not clasificar_paisaje(["Ortigosa del Monte train station"])[0]
    assert not clasificar_paisaje(["Cabanillas del Monte shearing shed"])[0]
    # gallego y costa
    assert clasificar_paisaje(["Fervenza do Ézaro"])[0]
    assert clasificar_paisaje(["Praia de Niñóns"])[0]
    assert clasificar_paisaje(["Cabo Finisterre"])[0]


@pytest.mark.parametrize(
    "titulo,esperado",
    [
        ("EMBALSE DE SANTILLANA (6495112213)", "Embalse de Santillana"),
        ("Puente de Navalacarreta (2 de mayo de 2015, Boca del Asno, Segovia) 09", "Puente de Navalacarreta"),
        ("2011-06-05 Cascada del Purgatorio - panoramio", "Cascada del Purgatorio"),
        ("Pico de la Miel - 01", "Pico de la Miel"),
        ("Embalse del río Pirón2", "Embalse del río Pirón"),
        ("LaSierra9", "La Sierra"),
    ],
)
def test_limpiar_nombre(titulo, esperado):
    assert limpiar_nombre(titulo) == esperado


def test_entero_tolera_nan():
    """El descubrimiento nacional cayó tras 5 h por `int(NaN or 0)`: los recuentos sin contar son NaN."""
    assert entero(np.nan) == 0 and entero(None) == 0 and entero(4.0) == 4 and entero("x") == 0


def _commons_grabado(params):
    datos = json.loads((FIX / "commons_detalles.json").read_text())
    pedidos = set(map(int, params["pageids"].split("|")))
    datos["query"]["pages"] = [p for p in datos["query"]["pages"] if p["pageid"] in pedidos]
    return datos


def test_galeria_con_respuestas_grabadas(monkeypatch):
    """Fotos cercanas de Commons → galería con autor y licencia de cada foto, autores distintos y meses."""
    monkeypatch.setattr(commons, "consultar", _commons_grabado)
    cerca = json.loads((FIX / "commons_geosearch.json").read_text())["query"]["geosearch"]
    fotos, autores, meses = galeria(cerca, None)
    assert fotos and autores >= 1 and len(meses) == 12
    for f in fotos:
        assert f["autor"] and f["licencia"] and f["url"].startswith("https://")
