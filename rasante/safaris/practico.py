"""Información práctica de cada parque para organizar el viaje.

- Cómo llegar: aeropuerto con vuelos regulares más cercano (OurAirports, dominio público) y pistas de
  aterrizaje dentro del parque (los safaris en avioneta de África aterrizan en ellas).
- Clima: climatología mensual de la NASA (POWER, una petición por punto, sin clave): lluvia y máxima media.
- OpenStreetMap (Overpass): alojamientos, operadores y agencias, puertas de entrada y pueblos cercanos. Es lo
  más lento: se hace por tandas y con caché, de más a menos importante.
"""

from __future__ import annotations

import csv
import io
import math
import re
import time

import requests

from rasante.comun.cache import CacheJson
from rasante.comun.red import sesion
from rasante.safaris.mundo import sin_tiempo

OURAIRPORTS = "https://davidmegginson.github.io/ourairports-data/airports.csv"
POWER = "https://power.larc.nasa.gov/api/temporal/climatology/point"
OVERPASS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
)
CACHE = CacheJson(prefijo="practico_", max_edad_s=80 * 86400)
_SESION = sesion()
DIAS_MES = (31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
MESES_POWER = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
TIPOS_ALOJAMIENTO = {
    "hotel": "hotel",
    "guest_house": "casa de huéspedes",
    "camp_site": "campamento",
    "chalet": "cabaña",
    "hostel": "albergue",
    "motel": "motel",
    "wilderness_hut": "refugio",
    "apartment": "apartamento",
}


def km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


class Aeropuertos:
    """Aeropuertos con vuelos regulares y pistas pequeñas, con búsqueda por rejilla de 1°."""

    def __init__(self, texto: str | None = None):
        if texto is None:
            texto = CACHE.leer("ourairports")
            if texto is None:
                r = _SESION.get(OURAIRPORTS, timeout=120)
                r.raise_for_status()
                texto = r.text
                CACHE.guardar("ourairports", texto)
        self.regulares: list[dict] = []
        self.pistas: dict[tuple[int, int], list[dict]] = {}
        for f in csv.DictReader(io.StringIO(texto)):
            try:
                a = {
                    "nombre": f["name"],
                    "lat": float(f["latitude_deg"]),
                    "lon": float(f["longitude_deg"]),
                    "iata": f["iata_code"] or None,
                    "ciudad": f["municipality"] or None,
                    "tipo": f["type"],
                }
            except ValueError:
                continue
            if f["scheduled_service"] == "yes" and f["type"] in ("large_airport", "medium_airport") and a["iata"]:
                self.regulares.append(a)
            elif f["type"] == "small_airport":
                self.pistas.setdefault((math.floor(a["lat"]), math.floor(a["lon"])), []).append(a)

    def llegar(self, lat: float, lon: float, radio_km: float) -> dict:
        p = (lat, lon)
        cercanos = sorted(self.regulares, key=lambda a: km(p, (a["lat"], a["lon"])))
        grande = next((a for a in cercanos if a["tipo"] == "large_airport"), None)
        salida = {"aeropuertos": []}
        for a in [cercanos[0], grande] if cercanos else []:
            if a and all(x["iata"] != a["iata"] for x in salida["aeropuertos"]):
                salida["aeropuertos"].append(
                    {
                        "nombre": a["nombre"],
                        "iata": a["iata"],
                        "ciudad": a["ciudad"],
                        "km": round(km(p, (a["lat"], a["lon"]))),
                        "internacional": a["tipo"] == "large_airport",
                        "lat": round(a["lat"], 4),
                        "lon": round(a["lon"], 4),
                    }
                )
        pistas = []
        celdas = range(-2, 3)
        for di in celdas:
            for dj in celdas:
                for a in self.pistas.get((math.floor(lat) + di, math.floor(lon) + dj), []):
                    d = km(p, (a["lat"], a["lon"]))
                    if d <= radio_km + 5:
                        pistas.append({"nombre": a["nombre"], "km": round(d)})
        pistas.sort(key=lambda a: a["km"])
        salida["pistas"] = pistas[:5]
        salida["n_pistas"] = len(pistas)
        return salida


def clima(lat: float, lon: float) -> dict | None:
    """Lluvia (mm al mes) y máxima media (°C) de cada mes, climatología de la NASA."""
    params = {
        "parameters": "PRECTOTCORR,T2M_MAX",
        "community": "AG",
        "latitude": round(lat, 2),
        "longitude": round(lon, 2),
        "format": "JSON",
    }
    clave = "power:" + repr(sorted(params.items()))
    d = CACHE.leer(clave)
    if d is None and sin_tiempo():
        return None
    if d is None:
        for intento in range(4):
            try:
                r = _SESION.get(POWER, params=params, timeout=60)
            except (requests.ConnectionError, requests.Timeout):
                time.sleep(5 * (intento + 1))
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(15 * (intento + 1))
                continue
            if r.status_code >= 400:  # punto fuera de la rejilla o similar
                return None
            d = r.json()["properties"]["parameter"]
            CACHE.guardar(clave, d)
            break
        else:
            return None
    lluvia, tmax = d.get("PRECTOTCORR", {}), d.get("T2M_MAX", {})
    if not lluvia or any(lluvia.get(m) is None or lluvia[m] < -900 for m in MESES_POWER):
        return None
    return {
        "lluvia_mm": [round(lluvia[m] * dias) for m, dias in zip(MESES_POWER, DIAS_MES, strict=True)],
        "tmax": [round(tmax[m]) if tmax.get(m) is not None and tmax[m] > -900 else None for m in MESES_POWER],
    }


def meses_secos(c: dict | None) -> list[int]:
    """Meses (1-12) con menos de 50 mm de lluvia: en los trópicos, la estación seca, la mejor para ver fauna."""
    if not c:
        return []
    return [i + 1 for i, v in enumerate(c["lluvia_mm"]) if v < 50]


PUERTA = re.compile(r"gate|entrance|puerta|entrada|porte|portão|portaria|tor\b", re.IGNORECASE)


def url_web(v: str | None) -> str | None:
    """En OSM muchas webs van sin esquema («www.lodge.com»): sin él, el enlace de la web no lleva a ningún sitio."""
    if not v:
        return None
    v = v.split(";")[0].strip()
    if not v or " " in v or "." not in v:
        return None
    return v if re.match(r"^https?://", v, re.IGNORECASE) else f"https://{v}"


OPERADOR = re.compile(r"safari|tour|travel|expedi|adventure|trek|wildlife|holiday|viaje", re.IGNORECASE)


def operadores_ciudad(lat: float, lon: float, nombre_ciudad: str | None = None) -> list[dict] | None:
    """Agencias y operadores de la ciudad de acceso (la del aeropuerto): Arusha para el Serengeti, Nairobi para
    el Masái Mara, Kasane para Chobe… Una consulta por ciudad, compartida por todos sus parques."""
    consulta = (
        "[out:json][timeout:60];"
        f'(nwr["office"~"^(travel_agent|guide|tourism)$"]["name"](around:25000,{lat},{lon});'
        f'nwr["shop"="travel_agency"]["name"](around:25000,{lat},{lon});'
        f'nwr["tourism"="information"]["information"="office"]["name"](around:25000,{lat},{lon}););'
        "out center tags 80;"
    )
    clave = "osm-ciudad:" + consulta
    datos = CACHE.leer(clave)
    if datos is None:
        if sin_tiempo():
            return None
        time.sleep(2)
        for url in OVERPASS:
            try:
                r = _SESION.post(url, data={"data": consulta}, timeout=80)
                r.raise_for_status()
                datos = r.json()
                break
            except (requests.RequestException, ValueError):
                continue
        if datos is None:
            return None
        CACHE.guardar(clave, datos)
    salida = []
    for e in datos.get("elements", []):
        t = e.get("tags", {})
        la = e.get("lat") or e.get("center", {}).get("lat")
        lo = e.get("lon") or e.get("center", {}).get("lon")
        if la is None or not t.get("name"):
            continue
        web = url_web(t.get("website") or t.get("contact:website") or t.get("url"))
        telefono = (t.get("phone") or t.get("contact:phone") or "").split(";")[0] or None
        email = t.get("email") or t.get("contact:email")
        if not (web or telefono or email):  # sin forma de contactar no sirve de nada
            continue
        salida.append(
            {
                "nombre": t["name"],
                "lat": round(la, 5),
                "lon": round(lo, 5),
                "km": round(km((lat, lon), (la, lo))),
                "web": web,
                "telefono": telefono,
                "email": email,
                "osm": f"{e['type']}/{e['id']}",
                "safari": bool(OPERADOR.search(t["name"])),
            }
        )
    # primero los que se dedican a viajes y safaris por el nombre y los que tienen web
    salida.sort(key=lambda o: (not o["safari"], o["web"] is None, o["km"]))
    return salida[:12]


def epoca(lat: float, temporada: list[int] | None, lluvia: list[int] | None, avistamientos: list[int]) -> dict:
    """Mejor época de cada parque (meses 1-12) y de dónde sale, para que ninguno se quede sin ella:
    1. la temporada escrita a mano (destacados);
    2. en los trópicos, la estación seca (< 50 mm al mes);
    3. en los trópicos sin estación seca (selva), los cuatro meses menos lluviosos;
    4. fuera de los trópicos, los meses con más mamíferos observados (≥ 60 % del mejor), que es cuando hay
       actividad, crías y buen tiempo para salir; si no hay datos, los meses menos lluviosos."""
    if temporada:
        return {"meses": sorted(temporada), "motivo": "recomendada"}
    tropical = abs(lat) <= 23.5
    if tropical and lluvia:
        secos = meses_secos({"lluvia_mm": lluvia})
        if 0 < len(secos) < 12:
            return {"meses": secos, "motivo": "estación seca"}
        orden = sorted(range(12), key=lambda i: lluvia[i])[:4]
        return {"meses": sorted(i + 1 for i in orden), "motivo": "menos lluvia"}
    if sum(avistamientos) >= 100:
        tope = max(avistamientos)
        return {"meses": [i + 1 for i, v in enumerate(avistamientos) if v >= 0.6 * tope], "motivo": "más avistamientos"}
    if lluvia:
        orden = sorted(range(12), key=lambda i: lluvia[i])[:5]
        return {"meses": sorted(i + 1 for i in orden), "motivo": "menos lluvia"}
    return {"meses": [], "motivo": None}


def _nombre_util(nombre: str) -> bool:
    """Fuera los códigos de acampada de travesía («12», «4R1 - Ribbon Lake West»)."""
    codigo = re.match(r"^([A-Z0-9]{1,4})(\s+-\s+.*)?$", nombre.strip())
    return not (codigo and any(c.isdigit() for c in codigo.group(1)))


def osm(lat: float, lon: float, radio_km: float, solo_cache: bool = False) -> dict | None:
    """Alojamientos, operadores, puertas y pueblos cercanos (None si no está en caché y `solo_cache`)."""
    # radios acotados: con círculos de 100 km Overpass tardaba más de un minuto por parque
    r_aloj = int(min(radio_km + 15, 60) * 1000)
    r_puertas = int(min(radio_km + 5, 60) * 1000)
    r_pueblos = int(min(radio_km + 40, 80) * 1000)
    tipos = "|".join(TIPOS_ALOJAMIENTO)
    consulta = (
        "[out:json][timeout:90];"
        f'nwr["tourism"~"^({tipos})$"]["name"](around:{r_aloj},{lat},{lon});out center tags 60;'
        f'(nwr["office"~"^(travel_agent|guide)$"]["name"](around:{r_pueblos},{lat},{lon});'
        f'nwr["shop"="travel_agency"]["name"](around:{r_pueblos},{lat},{lon}););out center tags 30;'
        f'node["barrier"="gate"]["name"](around:{r_puertas},{lat},{lon});out tags 60;'
        f'node["place"~"^(town|city)$"]["name"](around:{r_pueblos},{lat},{lon});out tags 15;'
    )
    clave = "osm:" + consulta
    datos = CACHE.leer(clave)
    if datos is None:
        if solo_cache or sin_tiempo():
            return None
        time.sleep(2)  # los espejos públicos piden no saturarlos
        for intento in range(2):
            for url in OVERPASS:
                try:
                    r = _SESION.post(url, data={"data": consulta}, timeout=100)
                    r.raise_for_status()
                    datos = r.json()
                    break
                except (requests.RequestException, ValueError):
                    continue
            if datos is not None:
                break
            time.sleep(30 * (intento + 1))
        if datos is None:
            return None
        CACHE.guardar(clave, datos)
    return clasificar(datos, lat, lon)


def clasificar(datos: dict, lat: float, lon: float) -> dict:
    salida: dict[str, list] = {"alojamientos": [], "operadores": [], "puertas": [], "pueblos": []}
    for e in datos.get("elements", []):
        t = e.get("tags", {})
        la = e.get("lat") or e.get("center", {}).get("lat")
        lo = e.get("lon") or e.get("center", {}).get("lon")
        if la is None or not t.get("name") or not _nombre_util(t["name"]):
            continue
        base = {
            "nombre": t.get("name:es") or t.get("name:en") or t["name"],
            "lat": round(la, 5),
            "lon": round(lo, 5),
            "km": round(km((lat, lon), (la, lo))),
        }
        contacto = {
            "web": url_web(t.get("website") or t.get("contact:website") or t.get("url")),
            "telefono": (t.get("phone") or t.get("contact:phone") or "").split(";")[0] or None,
            "email": t.get("email") or t.get("contact:email"),
            "osm": f"{e['type']}/{e['id']}",
        }
        if t.get("tourism") in TIPOS_ALOJAMIENTO:
            salida["alojamientos"].append({**base, **contacto, "tipo": TIPOS_ALOJAMIENTO[t["tourism"]]})
        elif t.get("office") in ("travel_agent", "guide") or t.get("shop") == "travel_agency":
            salida["operadores"].append({**base, **contacto})
        elif t.get("place") in ("town", "city"):
            salida["pueblos"].append({**base, "poblacion": t.get("population")})
        elif PUERTA.search(t["name"]):  # las verjas de fincas no interesan: solo las puertas del parque
            salida["puertas"].append(base)
    salida["alojamientos"].sort(key=lambda a: (a["web"] is None, a["km"]))
    salida["operadores"].sort(key=lambda a: (a["web"] is None and a["telefono"] is None, a["km"]))
    for k in ("puertas", "pueblos"):
        salida[k].sort(key=lambda a: a["km"])
    salida["alojamientos"] = salida["alojamientos"][:30]
    salida["operadores"] = salida["operadores"][:15]
    salida["puertas"] = salida["puertas"][:8]
    salida["pueblos"] = salida["pueblos"][:5]
    return salida
