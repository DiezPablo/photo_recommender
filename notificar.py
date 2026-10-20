#!/usr/bin/env python3
"""
notificar.py — Envía por Telegram los mejores spots del día (o de mañana).

Extra opcional, desacoplado de la web. Lee public/datos/informe.json (de condiciones.py), se queda con lo que supera el
umbral y manda un mensaje con hora, nota, motivo y enlace para llegar.

Configuración (variables de entorno):
  TELEGRAM_TOKEN    token del bot (te lo da @BotFather)
  TELEGRAM_CHAT_ID  tu chat (sácalo con: python notificar.py --chat-id)
  WEB_URL           opcional, para enlazar la ficha (https://photo-recommender.vercel.app)

Uso:
  python notificar.py --prueba          # imprime el mensaje sin enviarlo
  python notificar.py                   # antes de las 14:00 → hoy; después → mañana
  python notificar.py --fecha 2026-10-20 --umbral 7
  python notificar.py --chat-id         # escribe algo a tu bot antes de lanzarlo
"""
from __future__ import annotations

import argparse
import html
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API = "https://api.telegram.org/bot{token}/{metodo}"
ICONOS = {"amanecer": "🌅", "atardecer": "🌇", "astro": "🌌", "niebla": "🌫️"}
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def elegir_fecha(arg: str | None, tz: ZoneInfo) -> str:
    if arg:
        return arg
    ahora = datetime.now(tz)
    return (ahora.date() + timedelta(days=1 if ahora.hour >= 14 else 0)).isoformat()


def filas_del_dia(informe: dict, fecha: str) -> list[dict]:
    """Aplana el informe de condiciones.py: una fila por spot y tipo de salida."""
    filas = []
    for s in informe.get("spots", []):
        d = next((d for d in s["dias"] if d["fecha"] == fecha), None)
        if not d:
            continue
        horas = {"amanecer": d["sol"]["amanecer"], "atardecer": d["sol"]["atardecer"],
                 "astro": f"{d['noche']['ini']}–{d['noche']['fin']}", "niebla": d["sol"]["amanecer"]}
        for momento, n in d["notas"].items():
            motivos = sorted(n["desglose"][1:], key=lambda f: -abs(f["puntos"]))[:2]
            filas.append({"spot": s["nombre"], "id": s["id"], "lat": s["lat"], "lon": s["lon"],
                          "momento": momento, "hora": horas.get(momento) or "", "nota": n["nota"],
                          "detalle": " · ".join(f["texto"] for f in motivos)})
    return filas


def construir_mensaje(informe: dict, fecha: str, umbral: float, top: int,
                      web: str | None = None) -> str | None:
    del_dia = filas_del_dia(informe, fecha)
    buenos = sorted((r for r in del_dia if r["nota"] >= umbral), key=lambda r: -r["nota"])[:top]
    d = datetime.fromisoformat(fecha)
    cabecera = f"📷 <b>Fotografía de paisaje · {DIAS[d.weekday()]} {d.day}/{d.month}</b>"
    if not buenos:
        if not del_dia:
            return None
        mejor = max(del_dia, key=lambda r: r["nota"])
        return (f"{cabecera}\n\nNada destaca (umbral {umbral:g}). Lo mejor: "
                f"{ICONOS.get(mejor['momento'], '')} {html.escape(mejor['spot'])} "
                f"({mejor['momento']}) con {mejor['nota']:g}/10.")
    lineas = [cabecera, ""]
    for r in buenos:
        mapa = f"https://www.google.com/maps/dir/?api=1&destination={r['lat']},{r['lon']}"
        enlaces = f'<a href="{html.escape(mapa)}">Cómo llegar</a>'
        if web:
            enlaces += f' · <a href="{html.escape(web.rstrip("/"))}/spot/{r["id"]}">Ficha</a>'
        lineas.append(
            f"{ICONOS.get(r['momento'], '•')} <b>{r['nota']:g}/10 · {html.escape(r['spot'])}</b>\n"
            f"{r['momento'].capitalize()} {r['hora']}\n"
            f"<i>{html.escape(r['detalle'])}</i>\n{enlaces}\n")
    return "\n".join(lineas).strip()


def enviar(token: str, chat_id: str, texto: str) -> None:
    r = requests.post(API.format(token=token, metodo="sendMessage"), timeout=30, json={
        "chat_id": chat_id, "text": texto, "parse_mode": "HTML",
        "disable_web_page_preview": True,
    })
    if not r.ok or not r.json().get("ok"):
        raise SystemExit(f"Telegram rechazó el mensaje: {r.text}")


def mostrar_chat_id(token: str) -> None:
    r = requests.get(API.format(token=token, metodo="getUpdates"), timeout=30).json()
    chats = {(u["message"]["chat"]["id"], u["message"]["chat"].get("first_name", ""))
             for u in r.get("result", []) if "message" in u}
    if not chats:
        print("No hay mensajes: escribe cualquier cosa a tu bot en Telegram y repite.")
    for cid, nombre in chats:
        print(f"TELEGRAM_CHAT_ID={cid}   ({nombre})")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--informe", default="public/datos/informe.json")
    p.add_argument("--fecha")
    p.add_argument("--umbral", type=float, default=6.5)
    p.add_argument("--top", type=int, default=5)
    p.add_argument("--tz", default="Europe/Madrid")
    p.add_argument("--prueba", action="store_true", help="no envía, solo imprime")
    p.add_argument("--silencio", action="store_true", help="no enviar si nada supera el umbral")
    p.add_argument("--chat-id", action="store_true", help="muestra tu chat id")
    a = p.parse_args()

    token = os.environ.get("TELEGRAM_TOKEN", "")
    if a.chat_id:
        return mostrar_chat_id(token)

    informe = json.loads(Path(a.informe).read_text())
    fecha = elegir_fecha(a.fecha, ZoneInfo(a.tz))
    texto = construir_mensaje(informe, fecha, a.umbral, a.top, os.environ.get("WEB_URL"))
    if texto is None:
        print(f"El informe no tiene datos para {fecha}")
        return
    if a.silencio and "Nada destaca" in texto:
        print("Nada supera el umbral; no envío.")
        return
    if a.prueba:
        print(texto)
        return
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise SystemExit("Faltan TELEGRAM_TOKEN y/o TELEGRAM_CHAT_ID")
    enviar(token, chat_id, texto)
    print(f"Enviado ({fecha})")


if __name__ == "__main__":
    main()
