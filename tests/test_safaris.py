"""Safaris: catálogo curado y lectura de iNaturalist con respuestas reales grabadas (Serengeti, bisonte)."""

import json

import pytest
from conftest import FIX

from rasante.safaris import entorno, inat
from rasante.safaris.catalogo import CSV, TIPOS, cargar
from rasante.safaris.cli import meses_relativos, recientes

GRABADO = json.loads((FIX / "inat_safaris.json").read_text())
SERENGETI = {"id": "serengeti", "lat": -2.33, "lon": 34.83, "radio_km": 60, "estrella": ["Panthera leo"]}


def test_catalogo():
    parques = cargar()
    assert len(parques) >= 60
    assert {p["continente"] for p in parques} >= {"África", "Asia", "América", "Oceanía"}
    for p in parques:
        assert set(p["tipos"]) <= TIPOS and p["meses"] and p["consejo"]
        assert p["wikidata"] is None or p["wikidata"].startswith("Q")
        # las tasas, siempre con su contexto (año, «aprox.» o el tipo de permiso)
        if p["tasa"]:
            assert any(x in p["tasa"] for x in ("20", "aprox", "Permiso")), p["id"]


def test_catalogo_con_coma_sin_comillas(tmp_path):
    f = tmp_path / "s.csv"
    cabecera = CSV.read_text().splitlines()[0]
    f.write_text(cabecera + "\nx,X,País,África,,0,0,10,4x4,1,,,Uno, dos\n")
    with pytest.raises(ValueError, match="comillas"):
        cargar(f)


@pytest.fixture
def inat_grabado(monkeypatch):
    def falso(ruta, params, cache=None):
        if ruta == "taxa":
            return GRABADO["taxa_bison"]
        if ruta == "observations/histogram":
            return GRABADO["meses_serengeti"]
        return GRABADO["conteos_serengeti"]

    monkeypatch.setattr(inat, "_get", falso)


def test_sinonimo_de_inaturalist(inat_grabado):
    t = inat.taxon("Bison bison")  # en iNaturalist es Bos bison
    assert t["cientifico"] == "Bos bison" and t["grupo"] == "Mammalia"


def test_conteos_y_meses(inat_grabado):
    c = inat.conteos(SERENGETI, [41964, 41955, 42280])
    assert c[41964] > c[41955] > 100  # leones y guepardos
    m = inat.por_mes(SERENGETI, "Mammalia")
    assert len(m) == 12 and min(m) > 100
    rel = meses_relativos(m)
    assert max(rel) == 100 and rel[6] == 100  # julio, la migración en el norte


def test_subespecie_cuenta_para_la_especie(monkeypatch):
    respuesta = {"results": [{"count": 7, "taxon": {"id": 999, "ancestor_ids": [1, 42280, 999]}}]}
    monkeypatch.setattr(inat, "_get", lambda ruta, params, cache=None: respuesta)
    assert inat.conteos(SERENGETI, [42280]) == {42280: 7}


def test_pocas_observaciones_sin_meses():
    assert meses_relativos([1] * 12) is None


def test_alojamientos_sin_codigos_de_acampada():
    assert not entorno._nombre_util("4R1 - Ribbon Lake West")
    assert not entorno._nombre_util("12")
    assert entorno._nombre_util("1872 Inn") and entorno._nombre_util("Old Faithful Inn")


def test_recientes(monkeypatch):
    monkeypatch.setattr(inat, "taxon", lambda c: {"taxon": 41964, "cientifico": c})
    monkeypatch.setattr(inat, "conteos", lambda p, ids, desde=None, cache=None: {41964: 12})
    monkeypatch.setattr(
        inat,
        "especies",
        lambda p, g, n, desde=None, cache=None: [
            {"taxon": 41964, "cientifico": "Panthera leo", "nombre": "León", "n": 12}
        ],
    )
    from datetime import date

    r = recientes([SERENGETI], hoy=date(2026, 10, 25))
    assert r["desde"] == "2026-09-25"
    assert r["parques"]["serengeti"]["estrella"] == {"41964": 12}
