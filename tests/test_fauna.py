"""Fauna: observatorios de OSM agrupados y resumen de GBIF con una respuesta real grabada."""

import json

import pytest
from conftest import FIX

from rasante.fauna import gbif
from rasante.fauna.cli import calcular
from rasante.fauna.osm import agrupar, leer_observatorios

GBIF = json.loads((FIX / "gbif_gallocanta.json").read_text())


@pytest.fixture
def gbif_grabado(monkeypatch, tmp_path):
    from rasante.comun.cache import CacheJson

    monkeypatch.setattr(gbif, "CACHE", CacheJson(tmp_path, prefijo="gbif_"))

    def falso(ruta, params):
        if ruta == "occurrence/search":
            return GBIF["ocurrencias"]
        if ruta.endswith("vernacularNames"):
            return GBIF["nombres"]
        return GBIF["especie"]

    monkeypatch.setattr(gbif, "_get", falso)


def test_observatorios_y_grupos():
    obs = leer_observatorios(FIX / "fauna.osm")
    assert len(obs) == 4  # sin el privado ni el parque
    grupos = agrupar(obs)
    assert len(grupos) == 2
    laguna = next(g for g in grupos if g["observatorios"] == 3)
    assert laguna["nombre"] == "Observatorio de Los Aguanares"  # el grupo toma el nombre del que lo tiene


def test_resumen_y_nombre_comun(gbif_grabado):
    r = gbif.resumen(40.98, -1.51)
    assert r["observaciones"] > 1000
    assert r["n_especies"] > 50
    assert len(r["meses"]) == 12 and sum(r["meses"]) > 0
    assert gbif.nombre_comun(2474950) == {"cientifico": "Grus grus", "clase": "ave", "nombre": "Grulla común"}


def test_calcular_lugares(gbif_grabado):
    lugares = calcular(agrupar(leer_observatorios(FIX / "fauna.osm")))
    assert len(lugares) == 2
    l0 = lugares[0]
    assert l0["ccaa"] == "Aragón" and l0["provincia"] in ("Zaragoza", "Teruel")
    assert l0["especies"][0]["nombre"] == "Grulla común"
    assert l0["id"] and l0["observaciones"] > 0
    # el que no tiene nombre en OSM se nombra por el pueblo más cercano
    assert any(lu["nombre"] == "Observatorio junto a Bello" for lu in lugares)
