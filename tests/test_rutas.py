"""rutas.py: geometría, métricas y lectura de OSM con un PBF sintético (sin red)."""
import math

import pytest

import rutas as R


def test_codificar_ejemplo_de_google():
    # ejemplo de la documentación del algoritmo (lat, lon) → "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
    coords = [(-120.2, 38.5), (-120.95, 40.7), (-126.453, 43.252)]
    assert R.codificar(coords) == "_p~iF~ps|U_ulLnnqC_mqNvxq`@"


def test_ordenar_tramos_une_y_da_la_vuelta():
    a = [(0.0, 0.0), (0.0, 0.01)]
    b = [(0.0, 0.02), (0.0, 0.01)]          # al revés
    c = [(0.0, 0.03), (0.0, 0.02)]          # al revés
    camino = R.ordenar_tramos([b, a, c])
    lats = [p[1] for p in camino]
    assert lats == sorted(lats) or lats == sorted(lats, reverse=True)
    assert {camino[0][1], camino[-1][1]} == {0.0, 0.03}


def test_orientar_por_sentido_de_la_fuente():
    camino = [(0.0, 0.0), (0.0, 0.01), (0.0, 0.02)]
    assert R.orientar(camino, ((0.0, 0.02), (0.0, 0.0)))[0] == (0.0, 0.02)
    assert R.orientar(camino, ((0.0, 0.0), (0.0, 0.02)))[0] == (0.0, 0.0)


def test_desnivel_ignora_ruido_del_dem():
    llano_con_ruido = [700 + (2 if i % 2 else -2) for i in range(200)]
    assert R.desnivel(llano_con_ruido) == (0.0, 0.0)
    subida = [1000 + i * 5 for i in range(101)]               # +500 m
    s, b = R.desnivel(subida)
    assert 480 <= s <= 500 and b == 0


def test_tiempo_mide():
    # 12 km y +800/−800: horizontal 3 h, vertical 2 + 1,33 = 3,33 h → 3,33 + 1,5 = 4,83 h
    assert R.tiempo_mide(12, 800, 800) == pytest.approx(4.83, abs=0.01)
    assert R.tiempo_mide(8, 0, 0) == pytest.approx(2.0)


def test_muestrear_cada_30_m():
    coords = [(0.0, 0.0), (0.0, 0.009)]        # ~1 km hacia el norte
    pts = R.muestrear(coords, 30)
    assert 33 <= len(pts) <= 36
    assert pts[-1][2] == pytest.approx(R.metros(coords[0], coords[1]))


def test_tipo_ruta():
    assert R.tipo_ruta("PR-M 1", "Circular de la Pedriza", "rwn", {}) == "PR"
    assert R.tipo_ruta("GR 10", "Tramo 9", "nwn", {}) == "GR"
    assert R.tipo_ruta(None, "Camino de Santiago del Sureste", "nwn", {}) == "Camino de Santiago"
    assert R.tipo_ruta("E7", "European long distance path", "iwn", {}) == "Europeo"
    assert R.tipo_ruta(None, "Ruta de los Tarayes", "lwn", {}) == "Sendero"


def test_leer_osm_con_pbf_sintetico(tmp_path):
    osmium = pytest.importorskip("osmium")
    f = tmp_path / "prueba.osm.pbf"
    with osmium.SimpleWriter(str(f)) as w:
        for i in range(1, 7):
            w.add_node(osmium.osm.mutable.Node(id=i, location=(-3.9, 40.80 + i * 0.001)))
        w.add_way(osmium.osm.mutable.Way(id=10, nodes=[1, 2, 3], tags={"highway": "path"}))
        w.add_way(osmium.osm.mutable.Way(id=11, nodes=[3, 4, 5, 6], tags={"highway": "path"}))
        w.add_relation(osmium.osm.mutable.Relation(id=100, members=[("w", 10, ""), ("w", 11, "")],
                                                   tags={"type": "route", "route": "hiking", "name": "Senda de prueba",
                                                         "ref": "PR-M 99", "network": "rwn"}))
        # bici: fuera
        w.add_relation(osmium.osm.mutable.Relation(id=101, members=[("w", 10, "")],
                                                   tags={"type": "route", "route": "foot", "network": "rcn", "name": "Bici"}))
        # superruta (solo relaciones): fuera
        w.add_relation(osmium.osm.mutable.Relation(id=102, members=[("r", 100, "")],
                                                   tags={"type": "route", "route": "hiking", "name": "GR 999"}))
    rs = R.leer_osm(f)
    assert [r["id"] for r in rs] == ["osm-100"]
    r = rs[0]
    assert r["tipo"] == "PR" and r["ref"] == "PR-M 99"
    assert len(r["tramos"]) == 1 and len(r["tramos"][0]) == 6     # las dos vías unidas
    km = sum(R.longitud_m(t) for t in r["tramos"]) / 1000
    assert km == pytest.approx(5 * 0.001 * 111.32, rel=0.01)
