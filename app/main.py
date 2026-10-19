"""Servidor del bot: recibe el webhook de Telegram.

Arranque (desde la raíz del repo):
  python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

En local, sin URL pública, usa el modo polling:
  python -m app.polling
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from app.bot import Bot
from app.config import Config
from app.telegram import Telegram

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")


@asynccontextmanager
async def ciclo(app: FastAPI):
    cfg = Config()
    http = httpx.AsyncClient(timeout=30)
    tg = Telegram(cfg.telegram_token, http)
    app.state.cfg, app.state.bot = cfg, Bot(cfg, tg, http)
    if cfg.telegram_token and cfg.public_url:
        try:
            await tg.configurar(cfg.public_url, cfg.webhook_secret, cfg.webapp_url)
            log.info("Webhook registrado en %s", cfg.public_url)
        except Exception:
            log.exception("No se pudo configurar el webhook")
    yield
    await http.aclose()


app = FastAPI(title="Spots de paisaje", lifespan=ciclo)


@app.get("/")
async def salud():
    return {"ok": True}


@app.post("/telegram/webhook")
async def webhook(request: Request, tareas: BackgroundTasks,
                  x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    cfg: Config = request.app.state.cfg
    if cfg.webhook_secret and x_telegram_bot_api_secret_token != cfg.webhook_secret:
        raise HTTPException(status_code=403)
    tareas.add_task(request.app.state.bot.procesar, await request.json())
    return {"ok": True}   # respondemos ya; Telegram reintenta si tardamos
