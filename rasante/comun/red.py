"""Peticiones HTTP: User-Agent descriptivo (lo piden Wikimedia, OSM y Open-Meteo) y sesiones."""

from __future__ import annotations

import os

import requests

USER_AGENT = os.environ.get(
    "USER_AGENT",
    "spots-paisaje/0.3 (https://github.com/DiezPablo/photo_recommender; proyecto personal no comercial)",
)


def sesion() -> requests.Session:
    """Sesión HTTP con el User-Agent del proyecto (reutiliza conexiones)."""
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s
