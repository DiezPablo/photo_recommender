"""Los modelos publicados hasta oct-2026 (v1), para comparar con los actuales."""

from __future__ import annotations

from rasante.notas import valor


def nota_luz_v1(local: dict, horizonte_bajas: float) -> float:
    """El modelo publicado hasta oct-2026 (v1), para comparar."""
    L, M, H = valor(local, "cloud_cover_low"), valor(local, "cloud_cover_mid"), valor(local, "cloud_cover_high")
    P = valor(local, "precipitation_probability")
    lienzo = max(H, 0.8 * M)
    n = 4.0
    if lienzo < 15:
        n -= 1
    elif lienzo < 35:
        n += 1 + 2 * (lienzo - 15) / 20
    elif lienzo <= 70:
        n += 4
    else:
        n += 4 - 6 * (lienzo - 70) / 30
    if L > 30:
        n -= 3 * min(1, (L - 30) / 60)
    if horizonte_bajas > 30:
        n -= 3.5 * min(1, (horizonte_bajas - 30) / 60)
    elif lienzo >= 20 and horizonte_bajas < 15:
        n += 1
    n -= 3 * P / 100
    return max(0.0, min(10.0, n))


def niebla_v1(f: dict) -> float:
    """Fórmula de niebla publicada hasta oct-2026 (v1), en 0-1."""
    rh, t, td, v = (
        valor(f, "relative_humidity_2m"),
        valor(f, "temperature_2m"),
        valor(f, "dew_point_2m"),
        valor(f, "wind_speed_10m", 30),
    )
    c = lambda x: max(0.0, min(1.0, x))
    return c((rh - 85) / 12) * c((3 - (t - td)) / 3) * c((15 - v) / 12)
