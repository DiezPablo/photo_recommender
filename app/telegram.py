"""Cliente mínimo de la Bot API de Telegram (solo lo que usa el bot)."""
from __future__ import annotations

import httpx


class Telegram:
    def __init__(self, token: str, cliente: httpx.AsyncClient | None = None):
        self.base = f"https://api.telegram.org/bot{token}"
        self.http = cliente or httpx.AsyncClient(timeout=30)

    async def llamar(self, metodo: str, **datos):
        r = await self.http.post(f"{self.base}/{metodo}", json={k: v for k, v in datos.items() if v is not None})
        cuerpo = r.json()
        if not cuerpo.get("ok"):
            raise RuntimeError(f"Telegram {metodo}: {cuerpo.get('description')}")
        return cuerpo["result"]

    async def mensaje(self, chat_id: int, texto: str, teclado: dict | None = None):
        return await self.llamar("sendMessage", chat_id=chat_id, text=texto, parse_mode="HTML",
                                 disable_web_page_preview=True, reply_markup=teclado)

    async def responder_boton(self, callback_id: str, texto: str | None = None):
        return await self.llamar("answerCallbackQuery", callback_query_id=callback_id, text=texto)

    async def configurar(self, public_url: str, secreto: str, webapp_url: str):
        """Registra el webhook, los comandos y el botón de menú que abre la Mini App."""
        if public_url:
            await self.llamar("setWebhook", url=f"{public_url}/telegram/webhook",
                              secret_token=secreto or None,
                              allowed_updates=["message", "callback_query"])
        await self.llamar("setMyCommands", commands=[
            {"command": "hoy", "description": "Mejores spots de hoy"},
            {"command": "manana", "description": "Mejores spots de mañana"},
            {"command": "pasado", "description": "Mejores spots de pasado mañana"},
            {"command": "mapa", "description": "Abrir el mapa de spots"},
            {"command": "spot", "description": "Previsión de un spot: /spot nombre"},
            {"command": "ayuda", "description": "Qué puedo hacer"},
        ])
        if webapp_url:
            await self.llamar("setChatMenuButton", menu_button={
                "type": "web_app", "text": "Mapa", "web_app": {"url": webapp_url}})
