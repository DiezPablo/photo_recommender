"""Configuración del bot, toda por variables de entorno."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _lista_ids(valor: str) -> set[int]:
    return {int(v) for v in valor.replace(" ", "").split(",") if v}


@dataclass
class Config:
    telegram_token: str = field(default_factory=lambda: os.environ.get("TELEGRAM_TOKEN", ""))
    # Solo estos usuarios pueden usar el bot (tu id; sácalo con `python notificar.py --chat-id`)
    usuarios: set[int] = field(default_factory=lambda: _lista_ids(os.environ.get("ALLOWED_USER_IDS", "")))
    # URL pública de la Mini App (Cloudflare Pages o GitHub Pages)
    webapp_url: str = field(default_factory=lambda: os.environ.get("WEBAPP_URL", "").rstrip("/"))
    # De dónde leer informe.json y spots.geojson; por defecto, la carpeta datos/ de la Mini App
    datos_url: str = field(default_factory=lambda: os.environ.get("DATOS_URL", "").rstrip("/"))
    # URL pública de este servidor, para registrar el webhook al arrancar
    public_url: str = field(default_factory=lambda: os.environ.get("PUBLIC_URL", "").rstrip("/"))
    webhook_secret: str = field(default_factory=lambda: os.environ.get("WEBHOOK_SECRET", ""))
    # Opcional: para guardar spots propios en mis_spots.csv del repo y relanzar el cálculo
    github_token: str = field(default_factory=lambda: os.environ.get("GITHUB_TOKEN", ""))
    github_repo: str = field(default_factory=lambda: os.environ.get("GITHUB_REPO", ""))  # usuario/repo
    github_rama: str = field(default_factory=lambda: os.environ.get("GITHUB_BRANCH", "main"))
    radio_km: float = field(default_factory=lambda: float(os.environ.get("RADIO_KM", "80")))
    umbral: float = field(default_factory=lambda: float(os.environ.get("UMBRAL", "6.5")))
    tz: str = field(default_factory=lambda: os.environ.get("TZ_SPOTS", "Europe/Madrid"))

    def __post_init__(self):
        if not self.datos_url and self.webapp_url:
            self.datos_url = f"{self.webapp_url}/datos"

    @property
    def github_activo(self) -> bool:
        return bool(self.github_token and self.github_repo)
