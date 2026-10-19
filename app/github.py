"""Guarda spots propios en mis_spots.csv del repo y relanza el cálculo de condiciones."""
from __future__ import annotations

import base64
import csv
import io

import httpx

API = "https://api.github.com"


def _cabeceras(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def linea_csv(nombre: str, lat: float, lon: float, tipo: str = "", momentos: str = "") -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow([nombre, f"{lat:.5f}", f"{lon:.5f}", tipo, momentos])
    return buf.getvalue()


async def anadir_spot(http: httpx.AsyncClient, token: str, repo: str, rama: str,
                      nombre: str, lat: float, lon: float, momentos: str = "") -> None:
    url = f"{API}/repos/{repo}/contents/mis_spots.csv"
    r = await http.get(url, params={"ref": rama}, headers=_cabeceras(token))
    if r.status_code == 404:
        actual, sha = "nombre,lat,lon,tipo,momentos\n", None
    else:
        r.raise_for_status()
        j = r.json()
        actual, sha = base64.b64decode(j["content"]).decode(), j["sha"]
    if not actual.endswith("\n"):
        actual += "\n"
    nuevo = actual + linea_csv(nombre, lat, lon, "", momentos)
    cuerpo = {"message": f"Nuevo spot desde Telegram: {nombre}",
              "content": base64.b64encode(nuevo.encode()).decode(), "branch": rama}
    if sha:
        cuerpo["sha"] = sha
    r = await http.put(url, json=cuerpo, headers=_cabeceras(token))
    r.raise_for_status()


async def relanzar_datos(http: httpx.AsyncClient, token: str, repo: str, rama: str) -> bool:
    """Lanza el workflow datos.yml para que el spot nuevo tenga nota cuanto antes."""
    r = await http.post(f"{API}/repos/{repo}/actions/workflows/datos.yml/dispatches",
                        json={"ref": rama, "inputs": {"enviar": "false"}}, headers=_cabeceras(token))
    return r.status_code == 204
