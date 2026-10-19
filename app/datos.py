"""Lectura de informe.json y spots.geojson (publicados junto a la Mini App) con caché corta."""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

TTL_S = 600
_cache: dict[str, tuple[float, dict]] = {}
LOCALES = {"informe.json": [Path("docs/datos/informe.json"), Path("salida/informe.json")],
           "spots.geojson": [Path("docs/datos/spots.geojson"), Path("salida/spots.geojson")]}


async def _leer(nombre: str, base_url: str, http: httpx.AsyncClient) -> dict:
    ahora = time.time()
    if nombre in _cache and ahora - _cache[nombre][0] < TTL_S:
        return _cache[nombre][1]
    datos = None
    if base_url:
        try:
            r = await http.get(f"{base_url}/{nombre}", params={"t": int(ahora // TTL_S)})
            if r.status_code == 200:
                datos = r.json()
        except httpx.HTTPError:
            pass
    if datos is None:  # sin URL o caída: ficheros locales (útil en desarrollo)
        for p in LOCALES[nombre]:
            if p.exists():
                datos = json.loads(p.read_text())
                break
    if datos is None:
        datos = {"resultados": []} if nombre == "informe.json" else {"features": []}
    _cache[nombre] = (ahora, datos)
    return datos


async def informe(base_url: str, http: httpx.AsyncClient) -> dict:
    return await _leer("informe.json", base_url, http)


async def spots(base_url: str, http: httpx.AsyncClient) -> dict:
    return await _leer("spots.geojson", base_url, http)


def limpiar_cache():
    _cache.clear()
