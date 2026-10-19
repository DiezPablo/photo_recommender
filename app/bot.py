"""Lógica del bot: comandos, ubicación y guardado de spots propios."""
from __future__ import annotations

import html
import logging
import math
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

import notificar
from app import datos, github
from app.config import Config
from app.telegram import Telegram

log = logging.getLogger("bot")
ICONOS = notificar.ICONOS
DIAS = notificar.DIAS
MOMENTOS_VALIDOS = {"amanecer", "atardecer", "astro", "niebla"}


def _normal(texto: str) -> str:
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def distancia_km(lat1, lon1, lat2, lon2) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (lat1, lon1, lat2, lon2))
    a = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))


def _etiqueta_dia(fecha: str, hoy: str) -> str:
    d = datetime.fromisoformat(fecha).date()
    delta = (d - datetime.fromisoformat(hoy).date()).days
    return {0: "hoy", 1: "mañana", 2: "pasado"}.get(delta, f"{DIAS[d.weekday()]} {d.day}")


class Bot:
    def __init__(self, cfg: Config, tg: Telegram, http: httpx.AsyncClient):
        self.cfg, self.tg, self.http = cfg, tg, http
        self.pendientes: dict[int, dict] = {}   # chat → spot a la espera de nombre

    # ------------------------------------------------------------ utilidades
    def hoy(self) -> str:
        return datetime.now(ZoneInfo(self.cfg.tz)).date().isoformat()

    def teclado_mapa(self) -> dict | None:
        if not self.cfg.webapp_url:
            return None
        return {"inline_keyboard": [[{"text": "🗺️ Abrir mapa", "web_app": {"url": self.cfg.webapp_url}}]]}

    async def informe(self) -> dict:
        return await datos.informe(self.cfg.datos_url, self.http)

    # -------------------------------------------------------------- entrada
    async def procesar(self, update: dict) -> None:
        try:
            if "callback_query" in update:
                await self._boton(update["callback_query"])
            elif "message" in update:
                await self._mensaje(update["message"])
        except Exception:  # un fallo en un mensaje no debe tumbar el webhook
            log.exception("Error procesando update")
            chat = (update.get("message") or update.get("callback_query", {}).get("message") or {}).get("chat", {})
            if chat.get("id"):
                await self.tg.mensaje(chat["id"], "⚠️ Algo ha fallado. Prueba otra vez en un rato.")

    async def _autorizado(self, usuario: dict, chat_id: int) -> bool:
        if usuario.get("id") in self.cfg.usuarios:
            return True
        if not self.cfg.usuarios:
            await self.tg.mensaje(chat_id, (
                "🔒 Este bot aún no tiene usuarios autorizados.\n"
                f"Tu id de Telegram es <code>{usuario.get('id')}</code>: ponlo en la variable "
                "<code>ALLOWED_USER_IDS</code> del servidor y reinícialo."))
        return False

    async def _mensaje(self, m: dict) -> None:
        chat_id = m["chat"]["id"]
        if not await self._autorizado(m.get("from", {}), chat_id):
            return
        if "location" in m:
            return await self.cerca_de(chat_id, m["location"]["latitude"], m["location"]["longitude"])
        texto = (m.get("text") or "").strip()
        if not texto:
            return
        if not texto.startswith("/") and chat_id in self.pendientes:
            return await self.guardar_spot(chat_id, texto)
        comando, _, arg = texto.partition(" ")
        comando = comando.split("@")[0].lower()
        if comando in ("/start", "/ayuda", "/help"):
            await self.ayuda(chat_id)
        elif comando in ("/hoy", "/manana", "/mañana", "/pasado"):
            dias = {"/hoy": 0, "/manana": 1, "/mañana": 1, "/pasado": 2}[comando]
            await self.resumen_dia(chat_id, dias)
        elif comando == "/mapa":
            await self.tg.mensaje(chat_id, "Aquí tienes el mapa de spots con la nota de cada día.",
                                  self.teclado_mapa())
        elif comando == "/spot":
            await self.ficha_spot(chat_id, arg.strip())
        elif comando == "/cancelar":
            self.pendientes.pop(chat_id, None)
            await self.tg.mensaje(chat_id, "Cancelado.")
        else:
            await self.ficha_spot(chat_id, texto) if not texto.startswith("/") else await self.ayuda(chat_id)

    async def _boton(self, q: dict) -> None:
        chat_id = q["message"]["chat"]["id"]
        if not await self._autorizado(q.get("from", {}), chat_id):
            return
        accion, *resto = (q.get("data") or "").split(":")
        if accion == "guardar" and len(resto) == 2:
            lat, lon = float(resto[0]), float(resto[1])
            self.pendientes[chat_id] = {"lat": lat, "lon": lon}
            await self.tg.responder_boton(q["id"])
            await self.tg.mensaje(chat_id, (
                "📍 ¿Cómo se llama este spot?\n"
                "Puedes añadir los momentos que te interesan tras una barra, por ejemplo:\n"
                "<code>Mirador de la presa | atardecer;astro</code>\n\n/cancelar para no guardarlo."))
        else:
            await self.tg.responder_boton(q["id"])

    # ------------------------------------------------------------- comandos
    async def ayuda(self, chat_id: int) -> None:
        await self.tg.mensaje(chat_id, (
            "📷 <b>Spots de paisaje</b>\n\n"
            "/hoy · /manana · /pasado — los mejores spots del día\n"
            "/spot <i>nombre</i> — previsión de un spot concreto\n"
            "/mapa — mapa con la nota de cada spot\n"
            "📎 Mándame tu <b>ubicación</b> (o la de cualquier sitio) y te digo qué hay cerca "
            "que merezca la pena, y si quieres lo guardo como spot propio."), self.teclado_mapa())

    async def resumen_dia(self, chat_id: int, dias: int) -> None:
        fecha = (datetime.fromisoformat(self.hoy()) + timedelta(days=dias)).date().isoformat()
        texto = notificar.construir_mensaje(await self.informe(), fecha, self.cfg.umbral, top=6)
        await self.tg.mensaje(chat_id, texto or "Todavía no hay previsión para ese día.", self.teclado_mapa())

    async def ficha_spot(self, chat_id: int, consulta: str) -> None:
        if not consulta:
            return await self.tg.mensaje(chat_id, "Dime el nombre: <code>/spot Picón</code>")
        res = (await self.informe())["resultados"]
        q = _normal(consulta)
        nombres = sorted({r["spot"] for r in res if q in _normal(r["spot"])})
        if not nombres:
            return await self.tg.mensaje(chat_id, f"No encuentro ningún spot con «{html.escape(consulta)}».")
        exactos = [n for n in nombres if _normal(n) == q]
        if len(nombres) > 1 and not exactos:
            lista = "\n".join(f"• <code>/spot {html.escape(n)}</code>" for n in nombres[:10])
            return await self.tg.mensaje(chat_id, f"Hay varios:\n{lista}")
        nombre = (exactos or nombres)[0]
        filas = [r for r in res if r["spot"] == nombre]
        hoy = self.hoy()
        lineas = [f"📍 <b>{html.escape(nombre)}</b>"]
        for fecha in sorted({r["fecha"] for r in filas}):
            if fecha < hoy:
                continue
            lineas.append(f"\n<b>{_etiqueta_dia(fecha, hoy).capitalize()}</b>")
            for r in sorted((r for r in filas if r["fecha"] == fecha), key=lambda r: r["hora"]):
                lineas.append(f"{ICONOS.get(r['momento'], '•')} {r['nota']:g}/10 {r['momento']} {r['hora']}\n"
                              f"<i>{html.escape(r['detalle'])}</i>")
        r0 = filas[0]
        lineas.append(f'\n<a href="https://www.google.com/maps/dir/?api=1&amp;destination={r0["lat"]},{r0["lon"]}">Cómo llegar</a>')
        await self.tg.mensaje(chat_id, "\n".join(lineas), self.teclado_mapa())

    async def cerca_de(self, chat_id: int, lat: float, lon: float) -> None:
        res = (await self.informe())["resultados"]
        hoy = self.hoy()
        manana = (datetime.fromisoformat(hoy) + timedelta(days=1)).date().isoformat()
        candidatos = []
        for r in res:
            if r["fecha"] not in (hoy, manana):
                continue
            d = distancia_km(lat, lon, r["lat"], r["lon"])
            if d <= self.cfg.radio_km:
                candidatos.append((r, d))
        candidatos.sort(key=lambda x: (-x[0]["nota"], x[1]))
        guardar = {"text": "➕ Guardar este sitio como spot", "callback_data": f"guardar:{lat:.5f}:{lon:.5f}"}
        teclado = {"inline_keyboard": [[guardar]] + (self.teclado_mapa() or {"inline_keyboard": []})["inline_keyboard"]}
        if not candidatos:
            return await self.tg.mensaje(chat_id, f"No tengo spots a menos de {self.cfg.radio_km:g} km.", teclado)
        lineas = [f"📍 <b>Lo mejor a menos de {self.cfg.radio_km:g} km</b>\n"]
        for r, d in candidatos[:6]:
            lineas.append(f"{ICONOS.get(r['momento'], '•')} <b>{r['nota']:g}/10 · {html.escape(r['spot'])}</b> "
                          f"({d:.0f} km)\n{_etiqueta_dia(r['fecha'], hoy).capitalize()} {r['momento']} {r['hora']}")
        await self.tg.mensaje(chat_id, "\n".join(lineas), teclado)

    async def guardar_spot(self, chat_id: int, texto: str) -> None:
        sitio = self.pendientes.pop(chat_id)
        nombre, _, momentos = (p.strip() for p in texto.partition("|"))
        momentos = ";".join(m for m in (_normal(x.strip()) for x in momentos.split(";")) if m in MOMENTOS_VALIDOS)
        nombre = nombre[:80] or "Spot sin nombre"
        if not self.cfg.github_activo:
            linea = github.linea_csv(nombre, sitio["lat"], sitio["lon"], "", momentos).strip()
            return await self.tg.mensaje(chat_id, (
                "No tengo acceso al repositorio (faltan GITHUB_TOKEN y GITHUB_REPO). "
                f"Añade esta línea a <code>mis_spots.csv</code>:\n<code>{html.escape(linea)}</code>"))
        await github.anadir_spot(self.http, self.cfg.github_token, self.cfg.github_repo,
                                 self.cfg.github_rama, nombre, sitio["lat"], sitio["lon"], momentos)
        relanzado = await github.relanzar_datos(self.http, self.cfg.github_token,
                                                self.cfg.github_repo, self.cfg.github_rama)
        await self.tg.mensaje(chat_id, (
            f"✅ Guardado <b>{html.escape(nombre)}</b>."
            + (" Recalculando la previsión: en unos minutos aparecerá en el mapa." if relanzado
               else " Tendrá nota en la próxima actualización de datos.")))
