"""Horizonte del terreno con un relieve sintético."""

from rasante.terreno import horizonte as H


def test_horizonte_con_terreno_sintetico(monkeypatch):
    """Una montaña de 1000 m al oeste a 5 km: el horizonte oeste se levanta ~10° y el este queda libre."""

    def altura(lat, lon, z=12):
        d_oeste = (-3.85 - lon) * 84_500  # metros al oeste del spot (1° de longitud ≈ 84,5 km a 40,7°)
        return 1000.0 if 4500 < d_oeste < 5500 and abs(lat - 40.72) < 0.02 else 0.0

    monkeypatch.setattr(H, "altura", altura)
    p = H.perfil(40.72, -3.85)
    assert 9 < H.angulo(p, 270) < 13
    assert H.angulo(p, 90) < 0.5
    dentro = lambda az, a, b: a <= az <= b if a <= b else az >= a or az <= b  # sectores que cruzan el norte
    assert any(dentro(90, a, b) for a, b in H.apertura(p))
    assert not any(dentro(270, a, b) for a, b in H.apertura(p))
