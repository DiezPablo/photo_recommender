"""Utilidades comunes: JSON publicado, identificadores y territorio (provincia, comunidad, fuera de España)."""

import json

from rasante.comun.ficheros import limpiar_json
from rasante.comun.ids import id_spot
from rasante.comun.territorio import CCAA_POR_PROVINCIA, PROVINCIAS, Provincias, ccaa_de
from rasante.spots.nombres import nombre_valido


def test_limpiar_json_quita_nan():
    import numpy as np

    assert limpiar_json({"a": float("nan"), "b": [np.float64(1.5), np.int64(2)], "c": float("inf")}) == {
        "a": None,
        "b": [1.5, 2],
        "c": None,
    }


def test_id_spot_estable_y_legible():
    a = id_spot("Mirador de la Barranca", 40.7712, -4.0012)
    assert a == id_spot("Mirador de la Barranca", 40.77121, -4.00119)
    assert a.startswith("mirador-de-la-barranca-")
    assert id_spot("Peñalara", 40.85, -3.95).startswith("penalara-")


def test_comunidad_por_codigo_ine():
    """El fichero de provincias de origen numeraba las comunidades de otra forma (Asturias salía «Ceuta»)."""
    assert len(CCAA_POR_PROVINCIA) == 52
    assert ccaa_de("Asturias") == "Principado de Asturias" and ccaa_de("A Coruña") == "Galicia"
    assert ccaa_de("Madrid") == "Comunidad de Madrid" and ccaa_de("Bizkaia/Vizcaya") == "País Vasco"
    g = json.loads((PROVINCIAS).read_text())
    for f in g["features"]:
        assert f["properties"]["ccaa"] == CCAA_POR_PROVINCIA[f["properties"]["cod_prov"]]


def test_fuera_de_espana_y_nombres_genericos():
    p = Provincias()
    assert p.de(39.39693, -7.37997) is None  # Marvão (Portugal) caía en Cáceres
    assert p.de(40.37254, -7.51653) is None  # Poço do Inferno, Serra da Estrela
    assert p.de(39.413, -7.244)["provincia"] == "Cáceres"  # Valencia de Alcántara, junto a la raya
    assert p.de(42.882, -9.272)["provincia"] == "A Coruña"  # Fisterra: en la costa sigue dentro
    assert p.de(42.047, -8.645)["provincia"] == "Pontevedra"  # Tui, en el Miño
    for n in ("Mural", "Picnic", "Begiratokia", "Mirador Rio", "calle de los cuchilleros", "Balcón Mirador"):
        assert not nombre_valido(n), n
    for n in ("Mirador de San Nicolás", "Torre de Hércules", "Playa de La Caleta", "Mirador del Ebro"):
        assert nombre_valido(n), n


def test_todos_los_modulos_se_importan():
    """Cada módulo del paquete se importa sin errores (los imports diferidos no los cubren los tests de lógica)."""
    import importlib
    import pkgutil

    import rasante

    for m in pkgutil.walk_packages(rasante.__path__, "rasante."):
        importlib.import_module(m.name)
