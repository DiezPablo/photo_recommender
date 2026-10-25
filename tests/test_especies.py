"""Especies emblemáticas: lista curada, zonas y meses con respuestas reales de GBIF (lince) grabadas."""

import json

import pytest
from conftest import FIX

from rasante.comun.territorio import Provincias
from rasante.eventos.naturaleza import cargar as cargar_eventos
from rasante.fauna import especies as es
from rasante.fauna import gbif

GRABADO = json.loads((FIX / "gbif_lince.json").read_text())


@pytest.fixture
def gbif_grabado(monkeypatch):
    def falso(ruta, params):
        clave = json.dumps({"ruta": ruta, "params": params if isinstance(params, dict) else [list(p) for p in params]})
        return GRABADO[clave]

    monkeypatch.setattr(gbif, "_get", falso)
    monkeypatch.setattr(es, "fotos", lambda cientificos: {})


def test_lista_curada():
    lista = es.cargar_lista()
    assert len(lista) >= 30
    assert len({e["id"] for e in lista}) == len(lista)
    eventos = {e["id"] for e in cargar_eventos()}
    for e in lista:
        assert e["grupo"] in es.GRUPOS
        assert set(e["eventos"]) <= eventos, e["id"]  # cada evento enlazado existe
    lince = next(e for e in lista if e["id"] == "lince-iberico")
    assert lince["eventos"] == ["lince-andujar"]


def test_lista_con_coma_sin_comillas(tmp_path):
    f = tmp_path / "especies.csv"
    f.write_text("id,nombre,cientifico,grupo,eventos,consejo\nx,X,Xus xus,ave,,Uno, dos\n")
    with pytest.raises(ValueError, match="comillas"):
        es.cargar_lista(f)


def test_lince_zonas_y_meses(gbif_grabado):
    lista = [e for e in es.cargar_lista() if e["id"] == "lince-iberico"]
    [lince] = es.calcular(lista)
    assert lince["gbif"] == 2435261
    assert lince["observaciones"] > 300
    # el celo, en pleno invierno: el mes más fácil es diciembre o enero; en verano casi no se ve
    assert lince["meses"].index(100) in (0, 11)
    assert max(lince["meses"][5:8]) < 30
    zonas = lince["zonas"]
    assert zonas[0]["provincia"] == "Jaén" and zonas[0]["peso"] == 100  # Sierra de Andújar
    assert "Huelva" in {z["provincia"] for z in zonas}  # Doñana
    assert all(z["ccaa"] == "Andalucía" for z in zonas)
    assert lince["foto"] is None


def test_indice_meses_quita_el_esfuerzo():
    # la misma proporción todos los meses: plano aunque en primavera haya el triple de observaciones
    assert es.indice_meses([10, 30, 10], [100, 300, 100]) == [100, 100, 100]
    assert es.indice_meses([0, 5, 10], [0, 100, 100]) == [0, 50, 100]


def test_zona_en_el_mar_toma_la_provincia_de_la_costa():
    provincias = Provincias()
    assert es.provincia_cercana(provincias, 35.95, -5.6)["provincia"] == "Cádiz"  # en el Estrecho
    assert es.provincia_cercana(provincias, 38.0, -14.0) is None  # mar adentro


def test_formas_domesticas_fuera(monkeypatch):
    def falso(ruta, params):
        if ruta == "occurrence/search":
            return {"facets": [{"field": "ACCEPTED_TAXON_KEY", "counts": [{"name": "6164210"}, {"name": "5219173"}]}]}
        return {"canonicalName": "Canis lupus familiaris"}

    monkeypatch.setattr(gbif, "_get", falso)
    assert es.filtro_taxon(5219173) == [("acceptedTaxonKey", 5219173)]
