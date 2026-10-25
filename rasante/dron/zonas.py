"""Descarga de las capas de zonas (servicios ArcGIS REST públicos) y clasificación de cada zona.

- ENAIRE, zonas geográficas UAS del RD 517/2024: aeronáuticas (aeropuertos, helipuertos, zonas militares) e
  infraestructuras (incluidas las ferroviarias de ADIF). Su capa «urbana» no sirve aquí: son cuatro regiones
  policiales que cubren toda España (a quién se comunica un vuelo en ciudad), no los núcleos urbanos.
- Agencia Europea de Medio Ambiente: espacios naturales protegidos de España (NatDA, antes CDDA) y Red Natura 2000.
  ENAIRE ya no publica la capa de medio ambiente: la normativa de los espacios naturales la pone cada gestor.

Cada zona acaba con un nivel: «no» (no se puede volar sin autorización expresa), «permiso» (hay que pedir
permiso o comunicarlo), «condiciones» (se puede volar con condiciones: altura máxima, época de cría…). Las
zonas que empiezan por encima de 120 m sobre el suelo (las TMA, por ejemplo) no afectan a la categoría abierta
y se descartan (`clasificar` devuelve None).
"""

from __future__ import annotations

import html
import json
import re
import time

import requests

from rasante.comun.cache import CacheJson
from rasante.comun.red import sesion

ENAIRE = "https://servais.enaire.es/insigniads/rest/services/NSF_SRV/SRV_UAS_ZG_data_V2/FeatureServer"
AEMA = "https://bio.discomap.eea.europa.eu/arcgis/rest/services/ProtectedSites"
CAPAS = {
    "aero": (f"{ENAIRE}/2", "1=1", "*"),
    "infraestructura": (f"{ENAIRE}/0", "1=1", "*"),
    "protegido": (
        f"{AEMA}/NatDAv24_Dyna_WM/MapServer/4",
        "countryCode='ES'",
        "siteName,designationTypeCode,iucnCategory",
    ),
    "natura": (f"{AEMA}/Natura2000_Dyna_WM/MapServer/0", "MS='ES'", "SITECODE,SITENAME,SITETYPE"),
}
PARQUE_NACIONAL = "ES08"  # código de designación de los parques nacionales en NatDA
SIMPLIFICAR = 0.0005  # ~50 m: suficiente para saber si un spot cae dentro
# las zonas cambian cada ciclo AIRAC (28 días) y la ejecución es mensual
CACHE = CacheJson(prefijo="dron_", max_edad_s=20 * 86400)
_SESION = sesion()


def _consultar(url: str, params: dict) -> dict:
    clave = json.dumps({"url": url, **params}, sort_keys=True)
    guardado = CACHE.leer(clave)
    if guardado is not None:
        return guardado
    for intento in range(5):
        try:
            r = _SESION.get(f"{url}/query", params=params, timeout=180)
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(10 * (intento + 1))
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(int(r.headers.get("Retry-After", 0) or 0) or 10 * (intento + 1))
            continue
        r.raise_for_status()
        datos = r.json()
        if "error" in datos:
            raise requests.HTTPError(f"{url}: {datos['error'].get('message')}")
        CACHE.guardar(clave, datos)
        return datos
    raise requests.ConnectionError(f"{url} no responde")


def descargar(capa: str, por_pagina: int = 500) -> list[dict]:
    """Todas las zonas de una capa como features GeoJSON (en páginas: el servidor limita cada respuesta)."""
    url, donde, campos = CAPAS[capa]
    features, desde = [], 0
    while True:
        d = _consultar(
            url,
            {
                "where": donde,
                "outFields": campos,
                "outSR": 4326,
                "maxAllowableOffset": SIMPLIFICAR,
                "resultOffset": desde,
                "resultRecordCount": por_pagina,
                "f": "geojson",
            },
        )
        features += d.get("features", [])
        if not d.get("exceededTransferLimit") and not d.get("properties", {}).get("exceededTransferLimit"):
            return features
        desde += por_pagina


def texto_plano(v: str | None) -> str:
    """El mensaje de ENAIRE viene en HTML: párrafos a saltos de línea y fuera etiquetas."""
    if not v:
        return ""
    v = re.sub(r"(?i)<\s*(p|br)\b[^>]*>", "\n", v)
    v = html.unescape(re.sub(r"<[^>]+>", "", v))
    return "\n".join(linea.strip() for linea in v.splitlines() if linea.strip())


def _metros(p: dict, campo: str) -> float | None:
    v = p.get(campo)
    if v is None:
        return None
    return v * 0.3048 if (p.get("uom") or "M").upper() == "FT" else v


ALTURA_MAXIMA = 120  # m sobre el suelo en la categoría abierta


def clasificar(capa: str, p: dict) -> dict | None:
    """Nivel, nombre y explicación de una zona a partir de sus propiedades (None si no afecta)."""
    p = {k.lower(): v for k, v in p.items()}  # ENAIRE devuelve unas veces Name y otras name
    if capa == "protegido":
        nacional = p.get("designationtypecode") == PARQUE_NACIONAL
        return {
            "capa": capa,
            "nivel": "no" if nacional else "permiso",
            "nombre": f"Parque Nacional {p['sitename']}" if nacional else p.get("sitename"),
            "texto": (
                "En los parques nacionales el vuelo de drones está prohibido salvo autorización expresa del parque."
                if nacional
                else "Espacio natural protegido: la mayoría exige autorización del órgano gestor para volar drones. "
                "Consulta su plan de uso y gestión."
            ),
        }
    if capa == "natura":
        zepa = p.get("sitetype") in ("A", "C")
        return {
            "capa": capa,
            "nivel": "condiciones",
            "nombre": p.get("sitename"),
            "texto": (
                "Red Natura 2000 (zona de especial protección para las aves): evita la época de cría y no te acerques "
                "a nidos ni colonias; algunas comunidades exigen autorización."
                if zepa
                else "Red Natura 2000: algunas comunidades exigen autorización o comunicación previa."
            ),
        }
    desde = _metros(p, "lower") or 0.0
    hasta = _metros(p, "upper")
    tipo = p.get("type")
    if (p.get("lowerreference") or "AGL").upper() == "AGL" and desde > ALTURA_MAXIMA:
        return None
    if capa == "infraestructura" and tipo == "CONDITIONAL":
        nivel, texto = "condiciones", texto_plano(p.get("message"))
    elif p.get("reasons") == "PRIVACY":
        # zonas restringidas al vuelo fotográfico (Defensa): se puede volar, pero hay que pedir las condiciones
        nivel, texto = "permiso", texto_plano(p.get("message"))
    elif desde > 0:
        # por debajo de cierta altura no hay que coordinar nada
        nivel, texto = "condiciones", texto_plano(p.get("message"))
    else:
        nivel, texto = ("no" if capa == "aero" else "permiso"), texto_plano(p.get("message"))
    return {
        "capa": capa,
        "nivel": nivel,
        "nombre": (texto_plano(p.get("name")).splitlines() or [None])[0],
        "texto": texto,
        "desde_m": round(desde) if desde else None,
        "hasta_m": round(hasta) if hasta is not None and hasta < 900 else None,
    }
