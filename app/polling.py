"""Modo desarrollo: el bot pregunta a Telegram por mensajes nuevos (sin URL pública).

  python -m app.polling

No lo uses a la vez que el webhook: Telegram solo permite uno de los dos.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from app.bot import Bot
from app.config import Config
from app.telegram import Telegram

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def main():
    cfg = Config()
    if not cfg.telegram_token:
        raise SystemExit("Falta TELEGRAM_TOKEN")
    async with httpx.AsyncClient(timeout=60) as http:
        tg = Telegram(cfg.telegram_token, http)
        await tg.llamar("deleteWebhook")
        await tg.configurar("", "", cfg.webapp_url)
        bot = Bot(cfg, tg, http)
        offset = 0
        logging.info("Escuchando mensajes… (Ctrl+C para salir)")
        while True:
            updates = await tg.llamar("getUpdates", offset=offset, timeout=50,
                                      allowed_updates=["message", "callback_query"])
            for u in updates:
                offset = u["update_id"] + 1
                await bot.procesar(u)


if __name__ == "__main__":
    asyncio.run(main())
