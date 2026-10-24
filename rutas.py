"""
rutas.py — Rutas de senderismo de toda España → public/datos/rutas.json

Fuentes (gratuitas y abiertas):
  - OpenStreetMap: relaciones route=hiking/foot de un extracto PBF de España (Geofabrik u openstreetmap.fr).
    Se lee el fichero entero sin consultas a Overpass. ODbL, con atribución.
  - Senderos homologados FEDME (GR, PR, SL) del servicio del IGN. CC BY 4.0 (FEDME). Cuando un sendero
    FEDME coincide con una ruta de OSM, se le pone el nombre oficial y el enlace a misendafedme.es; si no,
    entra como ruta propia.
  - Caminos Naturales (Ministerio de Agricultura, Pesca y Alimentación), mismo tratamiento.

Para cada ruta: trazado (simplificado a ~10 m, en «encoded polyline»), distancia, desnivel y perfil con el
modelo digital del terreno (horizonte.altura), tiempo y dificultad estimados con el método MIDE (sin el
medio ni la orientación, que no se conocen), circular o lineal, provincia y comunidad.

Uso:
  python rutas.py --pbf spain-latest.osm.pbf                 # → public/datos/rutas.json
  python rutas.py --pbf madrid.osm.pbf --sin-fedme --salida /tmp
"""
from __future__ import annotations

import argparse
import json
import math
import re
import time
from pathlib import Path

import requests
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import linemerge
from shapely.strtree import STRtree

import horizonte
from comun import USER_AGENT, ccaa_de, escribir_json

CACHE = Path("cache") / "rutas"
IGN = "https://nco.ign.es/server/rest/services/nco/{servicio}/MapServer/{capa}/query"
SERVICIOS_IGN = {"GR": ("GR", 1), "PR": ("PR", 1), "SL": ("SL", 1), "CN": ("CaminosNaturales", 1)}
SESION = requests.Session()
SESION.headers["User-Agent"] = USER_AGENT

# Roles de miembros que no son el camino principal
ROLES_FUERA = {"alternative", "excursion", "approach", "connection", "link", "guidepost", "platform", "stop"}
# Redes de bici, caballo… que a veces se cuelan con route=foot
RED_FUERA = re.compile(r"^(?:[lrni]cn|[lrni]hn)$")
PASO_M = 30                 # muestreo del perfil
SIMPLIFICAR_M = 10          # trazado de la ficha
SIMPLIFICAR_MAPA_M = 60     # trazado del mapa general
MAX_PERFIL = 160            # puntos del perfil que se guardan
M_POR_GRADO = 111_320.0


# ------------------------------------------------------------------ geometría ----
def metros(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distancia aproximada (m) entre dos puntos (lon, lat): equirrectangular, sobra para tramos cortos."""
    x = (b[0] - a[0]) * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot(x, b[1] - a[1]) * M_POR_GRADO


def longitud_m(coords: list[tuple[float, float]]) -> float:
    return sum(metros(coords[i], coords[i + 1]) for i in range(len(coords) - 1))


def ordenar_tramos(tramos: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    """Une los tramos de una ruta en un único recorrido: empieza por un extremo y va enlazando el tramo
    más cercano (dándole la vuelta si hace falta). Los saltos entre tramos no cuentan como distancia."""
    if not tramos:
        return []
    pendientes = [list(t) for t in tramos if len(t) >= 2]
    if not pendientes:
        return []
    # empezar por el tramo cuyo extremo esté más lejos de todos los demás (un extremo de la ruta)
    def aislamiento(t, i):
        p = t[i]
        return min((metros(p, o[j]) for o in pendientes if o is not t for j in (0, -1)), default=0)
    t0, extremo = max(((t, i) for t in pendientes for i in (0, -1)), key=lambda x: aislamiento(*x))
    pendientes.remove(t0)
    camino = list(t0) if extremo == 0 else list(t0[::-1])
    while pendientes:
        fin = camino[-1]
        mejor = min(((t, d) for t in pendientes for d in (0, -1)), key=lambda x: metros(fin, x[0][x[1]]))
        t, d = mejor
        pendientes.remove(t)
        camino.extend(t if d == 0 else t[::-1])
    return camino


def orientar(camino: list[tuple[float, float]], sentido) -> list[tuple[float, float]]:
    """Sentido de marcha. Con (principio, final) de la fuente (orden de los miembros de la relación o de
    la línea oficial), el recorrido empieza por el extremo más cercano al principio. Si no se sabe, se
    empieza por el extremo más bajo: en montaña las rutas lineales suelen subir desde el aparcamiento."""
    ini, fin = camino[0], camino[-1]
    if sentido:
        a, b = sentido
        if metros(a, b) > 200:
            al_reves = metros(fin, a) + metros(ini, b) < metros(ini, a) + metros(fin, b)
            return camino[::-1] if al_reves else camino
    if metros(ini, fin) < 300:
        return camino
    try:
        if horizonte.altura(fin[1], fin[0]) < horizonte.altura(ini[1], ini[0]) - 20:
            return camino[::-1]
    except (requests.RequestException, TypeError):
        pass
    return camino


def partes_unidas(lineas: list[list[tuple[float, float]]]) -> list[list[tuple[float, float]]]:
    """Fusiona las vías de una relación en tramos continuos."""
    if not lineas:
        return []
    m = linemerge(MultiLineString([LineString(l) for l in lineas if len(l) >= 2]))
    geoms = [m] if isinstance(m, LineString) else list(m.geoms)
    return [list(g.coords) for g in geoms if len(g.coords) >= 2]


def simplificar(coords: list[tuple[float, float]], tolerancia_m: float) -> list[tuple[float, float]]:
    if len(coords) < 3:
        return coords
    return list(LineString(coords).simplify(tolerancia_m / M_POR_GRADO, preserve_topology=False).coords)


def codificar(coords: list[tuple[float, float]], precision: int = 5) -> str:
    """Encoded polyline (algoritmo de Google): lat,lon con 5 decimales (~1 m), ~4 veces menos que JSON."""
    factor = 10 ** precision
    salida, plat, plon = [], 0, 0
    for lon, lat in coords:
        ilat, ilon = round(lat * factor), round(lon * factor)
        for v in (ilat - plat, ilon - plon):
            v = ~(v << 1) if v < 0 else v << 1
            while v >= 0x20:
                salida.append(chr((0x20 | (v & 0x1F)) + 63))
                v >>= 5
            salida.append(chr(v + 63))
        plat, plon = ilat, ilon
    return "".join(salida)


def muestrear(coords: list[tuple[float, float]], paso_m: float) -> list[tuple[float, float, float]]:
    """Puntos cada `paso_m` metros a lo largo del recorrido: (lon, lat, distancia acumulada en m).
    Los saltos de más de 500 m entre tramos no se recorren."""
    puntos = [(coords[0][0], coords[0][1], 0.0)]
    acum, resto = 0.0, 0.0
    for a, b in zip(coords, coords[1:]):
        d = metros(a, b)
        if d > 500 and len(coords) > 2:   # salto entre tramos sueltos
            puntos.append((b[0], b[1], acum))
            resto = 0.0
            continue
        pos = paso_m - resto
        while pos <= d:
            f = pos / d
            puntos.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, acum + pos))
            pos += paso_m
        resto = d - (pos - paso_m)
        acum += d
    if puntos[-1][2] < acum:
        puntos.append((coords[-1][0], coords[-1][1], acum))
    return puntos


# --------------------------------------------------------------- métricas ----
def desnivel(alturas: list[float]) -> tuple[float, float]:
    """Subida y bajada acumuladas. Se suaviza (media de 5 puntos, ~150 m) y se ignoran oscilaciones de
    menos de 3 m: el DEM a 30 m tiene ruido que inflaría el desnivel."""
    if len(alturas) < 2:
        return 0.0, 0.0
    k = 2
    suave = [sum(alturas[max(0, i - k):i + k + 1]) / len(alturas[max(0, i - k):i + k + 1]) for i in range(len(alturas))]
    subida = bajada = 0.0
    ref = suave[0]
    for h in suave[1:]:
        if h - ref >= 3:
            subida += h - ref
            ref = h
        elif ref - h >= 3:
            bajada += ref - h
            ref = h
    return subida, bajada


def tiempo_mide(km: float, subida: float, bajada: float) -> float:
    """Horas de marcha según el método MIDE (sin paradas): 4 km/h en llano, 400 m/h subiendo y 600 m/h
    bajando; el tiempo es el mayor de horizontal y vertical más la mitad del menor."""
    th = km / 4
    tv = subida / 400 + bajada / 600
    return max(th, tv) + min(th, tv) / 2


def dificultad(horas: float, subida: float, alt_max: float) -> str:
    """Esfuerzo estimado (no es la valoración MIDE oficial, que pide conocer el terreno)."""
    puntos = horas + subida / 500 + (1 if alt_max > 2000 else 0)
    if puntos < 3:
        return "fácil"
    if puntos < 6:
        return "moderada"
    if puntos < 10:
        return "difícil"
    return "muy difícil"


def tipo_ruta(ref: str | None, nombre: str | None, red: str | None, extra: dict) -> str:
    texto = f"{ref or ''} {nombre or ''}"
    if extra.get("pilgrimage") == "yes" or re.search(r"\bcamino de santiago|\bcamí de sant jaume|\bruta jacobea|\bvía de la plata\b", texto, re.I):
        return "Camino de Santiago"
    if re.search(r"\bE[- ]?\d{1,2}\b", ref or "") or red == "iwn":
        return "Europeo"
    if re.search(r"\bGR[- ]?\d", texto, re.I):
        return "GR"
    if re.search(r"\bPR[- ]", texto, re.I):
        return "PR"
    if re.search(r"\bSL[- ]", texto, re.I):
        return "SL"
    if re.search(r"camino natural", texto, re.I):
        return "Camino Natural"
    if re.search(r"v[ií]a verde", texto, re.I):
        return "Vía Verde"
    return "Sendero"


# -------------------------------------------------------------------- OSM ----
def leer_osm(pbf: Path) -> list[dict]:
    """Relaciones de senderismo con la geometría de sus vías. Dos pasadas por el fichero: relaciones
    (y sus vías) y vías con las coordenadas de sus nodos."""
    import osmium
    t0 = time.time()
    rels = {}
    for r in osmium.FileProcessor(str(pbf), osmium.osm.RELATION):
        tg = dict(r.tags)
        if tg.get("type") != "route" or tg.get("route") not in ("hiking", "foot"):
            continue
        if RED_FUERA.match(tg.get("network", "")) or tg.get("state") in ("proposed", "disused", "abandoned"):
            continue
        vias = [m.ref for m in r.members if m.type == "w" and m.role not in ROLES_FUERA]
        if not vias:      # superrutas (relaciones de relaciones): sus etapas ya están por separado
            continue
        rels[r.id] = {"tags": tg, "vias": vias}
    print(f"      {len(rels)} relaciones de senderismo ({time.time() - t0:.0f} s)", flush=True)
    necesarias = {w for r in rels.values() for w in r["vias"]}
    geom: dict[int, list[tuple[float, float]]] = {}
    proc = (osmium.FileProcessor(str(pbf), osmium.osm.NODE | osmium.osm.WAY).with_locations()
            .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY)).with_filter(osmium.filter.IdFilter(necesarias)))
    for w in proc:
        try:
            geom[w.id] = [(n.lon, n.lat) for n in w.nodes]
        except osmium.InvalidLocationError:
            continue
    print(f"      {len(geom)} vías con geometría ({time.time() - t0:.0f} s)", flush=True)
    rutas = []
    for rid, r in rels.items():
        tg = r["tags"]
        lineas = [geom[w] for w in r["vias"] if w in geom]
        if not lineas:
            continue
        nombre = tg.get("name") or tg.get("name:es")
        ref = tg.get("ref")
        if not nombre and not ref:
            continue
        # el orden de los miembros suele seguir el sentido oficial (de «from» a «to»)
        primera, ultima = lineas[0], lineas[-1]
        rutas.append({
            "sentido": (primera[len(primera) // 2], ultima[len(ultima) // 2]) if len(lineas) > 1 else None,
            "id": f"osm-{rid}", "osm": rid, "fuente": "osm", "nombre": nombre, "ref": ref,
            "red": tg.get("network"), "operador": tg.get("operator"), "web": tg.get("website") or tg.get("url"),
            "desde": tg.get("from"), "hasta": tg.get("to"), "descripcion": tg.get("description"),
            "circular_tag": tg.get("roundtrip"), "wikidata": tg.get("wikidata"),
            "tipo": tipo_ruta(ref, nombre, tg.get("network"), tg),
            "tramos": partes_unidas(lineas),
        })
    return rutas


# -------------------------------------------------------------------- IGN ----
def _ign(servicio: str, capa: int) -> list[dict]:
    """Todas las entidades de una capa del IGN en GeoJSON (paginado), con caché."""
    f = CACHE / f"ign_{servicio}_{capa}.json"
    if f.exists():
        return json.loads(f.read_text())
    url = IGN.format(servicio=servicio, capa=capa)
    feats, inicio = [], 0
    while True:
        for intento in range(5):
            try:
                r = SESION.get(url, params={"where": "1=1", "outFields": "*", "outSR": 4326, "f": "geojson",
                                            "resultOffset": inicio, "resultRecordCount": 200}, timeout=180)
                r.raise_for_status()
                lote = r.json().get("features", [])
                break
            except (requests.RequestException, ValueError):
                time.sleep(5 * (intento + 1))
        else:
            raise RuntimeError(f"IGN {servicio} no responde")
        feats += lote
        if len(lote) < 200:
            break
        inicio += len(lote)
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(feats))
    return feats


def _limpio(v) -> str | None:
    v = (v or "").strip() if isinstance(v, str) else v
    return v or None


def leer_ign() -> list[dict]:
    rutas = []
    for clave, (servicio, capa) in SERVICIOS_IGN.items():
        try:
            feats = _ign(servicio, capa)
        except RuntimeError as e:
            print(f"      {e}: se sigue sin esa fuente", flush=True)
            continue
        for k, f in enumerate(feats):
            p = {k2.split(".")[-1].lower(): v for k2, v in (f.get("properties") or {}).items()}
            g = f.get("geometry") or {}
            if g.get("type") == "LineString":
                lineas = [g["coordinates"]]
            elif g.get("type") == "MultiLineString":
                lineas = g["coordinates"]
            else:
                continue
            nombre = _limpio(p.get("nombre"))
            if not nombre:
                continue
            ref = None
            m = re.match(r"^((?:GR|PR|SL)[- ][A-Z]{0,3}[- ]?\d+(?:\.\d+)?)", nombre)
            if m:
                ref = m.group(1)
            fuente = "mapa" if clave == "CN" else "fedme"
            pl = lineas[0]
            rutas.append({
                "sentido": (tuple(pl[0][:2]), tuple(lineas[-1][-1][:2])),
                "id": f"{fuente}-{_limpio(p.get('id')) or p.get('objectid') or k}", "fuente": fuente,
                "nombre": nombre, "ref": ref, "red": None, "operador": "FEDME" if fuente == "fedme" else "MAPA",
                "web": _limpio(p.get("url_info")), "desde": None, "hasta": None, "descripcion": None,
                "circular_tag": None, "wikidata": None,
                "tipo": "Camino Natural" if clave == "CN" else tipo_ruta(ref, nombre, None, {}),
                "tramos": partes_unidas([[tuple(c[:2]) for c in l] for l in lineas]),
            })
        print(f"      IGN {clave}: {len(feats)}", flush=True)
    return rutas


def fusionar(osm: list[dict], oficiales: list[dict]) -> list[dict]:
    """Un sendero oficial que coincide con una ruta de OSM (≥ 70 % de su trazado a menos de ~50 m y
    longitud parecida) le da el nombre oficial y el enlace; si no, entra como ruta propia."""
    lineas = [MultiLineString(r["tramos"]) for r in osm]
    arbol = STRtree(lineas)
    buffers: dict[int, object] = {}
    sueltas = 0
    for o in oficiales:
        g = MultiLineString(o["tramos"])
        lo = g.length
        mejor, mejor_f = None, 0.0
        for i in arbol.query(g.buffer(0.0005)):
            if not (0.6 < lineas[i].length / max(lo, 1e-9) < 1.6):
                continue
            if i not in buffers:
                buffers[i] = lineas[i].buffer(0.0005)
            f = g.intersection(buffers[i]).length / max(lo, 1e-9)
            if f > mejor_f:
                mejor, mejor_f = i, f
        if mejor is not None and mejor_f >= 0.7:
            r = osm[mejor]
            r["nombre_osm"] = r["nombre"]
            r["nombre"] = o["nombre"]
            r["ref"] = o["ref"] or r["ref"]
            r["oficial"] = o["web"]
            r["fuente"] = f"osm+{o['fuente']}"
            if o["tipo"] in ("GR", "PR", "SL", "Camino Natural"):
                r["tipo"] = o["tipo"]
        else:
            osm.append(o)
            sueltas += 1
    print(f"      {len(oficiales) - sueltas} senderos oficiales coinciden con OSM, {sueltas} nuevos", flush=True)
    return osm


# ---------------------------------------------------------------- cálculo ----
def completar(r: dict, provincias) -> dict | None:
    """Recorrido, métricas y ubicación. None si la ruta no sirve (muy corta, fuera de España…)."""
    camino = ordenar_tramos(r["tramos"])
    if len(camino) < 2:
        return None
    km = sum(longitud_m(t) for t in r["tramos"]) / 1000
    if km < 0.5 or km > 1500:
        return None
    camino = orientar(camino, r.get("sentido"))
    ini, fin = camino[0], camino[-1]
    info = provincias.de(ini[1], ini[0]) or provincias.de(fin[1], fin[0])
    if not info:
        mitad = camino[len(camino) // 2]
        info = provincias.de(mitad[1], mitad[0])
    if not info:
        return None
    # perfil: en rutas muy largas basta un punto cada ~100 m
    pts = muestrear(simplificar(camino, 5), PASO_M if km < 60 else 100)
    alturas = []
    for lon, lat, _ in pts:
        try:
            alturas.append(horizonte.altura(lat, lon, 12 if km < 60 else 11))
        except (requests.RequestException, TypeError):
            alturas.append(float("nan"))
    validas = [h for h in alturas if h == h]
    if len(validas) < max(2, len(alturas) // 2):
        subida = bajada = 0.0
        alt_max = alt_min = None
        perfil = []
    else:
        ult = validas[0]
        alturas = [(ult := h) if h == h else ult for h in alturas]
        subida, bajada = desnivel(alturas)
        alt_max, alt_min = max(alturas), min(alturas)
        paso = max(1, math.ceil(len(pts) / MAX_PERFIL))
        perfil = [[round(pts[i][2] / 1000, 2), round(alturas[i])] for i in range(0, len(pts), paso)]
        if perfil[-1][0] != round(pts[-1][2] / 1000, 2):
            perfil.append([round(pts[-1][2] / 1000, 2), round(alturas[-1])])
    circular = r["circular_tag"] == "yes" or (r["circular_tag"] != "no" and metros(ini, fin) < 300)
    if circular:
        subida = bajada = max(subida, bajada)    # en una circular se sube lo que se baja
    horas = tiempo_mide(km, subida, bajada)
    simple = simplificar(camino, SIMPLIFICAR_M)
    xs, ys = [c[0] for c in camino], [c[1] for c in camino]
    nombre = r["nombre"] or r["ref"]
    return {
        "id": r["id"], "nombre": nombre, "ref": r["ref"] if r["ref"] and r["ref"] not in (nombre or "") else None,
        "tipo": r["tipo"], "fuente": r["fuente"], "osm": r.get("osm"), "oficial": r.get("oficial"),
        "web": r["web"], "operador": r["operador"], "desde": r["desde"], "hasta": r["hasta"],
        "descripcion": (r["descripcion"] or "")[:400] or None, "wikidata": r["wikidata"],
        "km": round(km, 1), "subida": round(subida), "bajada": round(bajada),
        "alt_max": None if alt_max is None else round(alt_max), "alt_min": None if alt_min is None else round(alt_min),
        "horas": round(horas, 1), "dificultad": dificultad(horas, subida, alt_max or 0), "circular": circular,
        "provincia": info["provincia"], "ccaa": ccaa_de(info["provincia"], info.get("ccaa")),
        "inicio": [round(ini[1], 5), round(ini[0], 5)], "fin": [round(fin[1], 5), round(fin[0], 5)],
        "bbox": [round(min(xs), 4), round(min(ys), 4), round(max(xs), 4), round(max(ys), 4)],
        "perfil": perfil, "linea": codificar(simple),
        "linea_mapa": codificar(simplificar(camino, SIMPLIFICAR_MAPA_M if km < 60 else 200)),
    }


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--pbf", required=True, help="extracto de OpenStreetMap de España (.osm.pbf)")
    a.add_argument("--salida", default="public/datos")
    a.add_argument("--sin-ign", action="store_true", help="solo OSM (pruebas sin red)")
    args = a.parse_args()
    from descubrir_espana import Provincias

    print("[1/4] OpenStreetMap…", flush=True)
    rutas = leer_osm(Path(args.pbf))
    print(f"      {len(rutas)} rutas con nombre", flush=True)
    if not args.sin_ign:
        print("[2/4] Senderos homologados FEDME y Caminos Naturales (IGN)…", flush=True)
        rutas = fusionar(rutas, leer_ign())
    print("[3/4] Recorrido, desnivel y tiempo…", flush=True)
    prov = Provincias()
    t0 = time.time()
    # en orden geográfico, para reutilizar las teselas del DEM y poder vaciar la caché en memoria
    rutas.sort(key=lambda r: (round(r["tramos"][0][0][1], 0), r["tramos"][0][0][0]) if r["tramos"] else (0, 0))
    salida = []
    for k, r in enumerate(rutas, 1):
        if not r["tramos"]:
            continue
        c = completar(r, prov)
        if c:
            salida.append(c)
        if len(horizonte._teselas) > 1500:
            horizonte._teselas.clear()
        if k % 500 == 0:
            print(f"      {k}/{len(rutas)} ({(time.time() - t0) / 60:.0f} min)", flush=True)
    vistos, unicas = set(), []
    for r in salida:
        if r["id"] not in vistos:
            vistos.add(r["id"])
            unicas.append(r)
    print("[4/4] Guardando…", flush=True)
    destino = Path(args.salida) / "rutas.json"
    escribir_json(destino, {
        "generado": time.strftime("%Y-%m-%dT%H:%M%z"),
        "fuentes": {"osm": "© colaboradores de OpenStreetMap (ODbL)", "fedme": "Senderos FEDME (CC BY 4.0)",
                    "mapa": "Caminos Naturales © Ministerio de Agricultura, Pesca y Alimentación",
                    "dem": "Teselas de elevación Terrarium (Mapzen/AWS Open Data)"},
        "rutas": unicas,
    })
    print(f"\n{len(unicas)} rutas → {destino} ({destino.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
