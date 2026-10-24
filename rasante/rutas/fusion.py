"""Fusión de fuentes, duplicados y nombres legibles."""

from __future__ import annotations

import re

from shapely.geometry import MultiLineString
from shapely.strtree import STRtree

from .geometria import metros


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


PRIORIDAD_FUENTE = {"osm+fedme": 5, "fedme": 4, "osm+mapa": 3, "osm": 2, "mapa": 1}


def quitar_duplicados(rutas: list[dict]) -> list[dict]:
    """La misma ruta puede venir dos veces (la etapa del GR 131 como sendero FEDME y como Camino Natural;
    tramos repetidos en los datos del Ministerio). Duplicado = salida y llegada a menos de 200 m (o
    intercambiadas) y la misma distancia (± 5 %). Se queda la de mejor fuente; si las dos tienen código
    oficial distinto (el GR 92 y el GR 249 comparten etapas) se quedan ambas."""

    def clave(p):
        return (round(p[0] / 0.002), round(p[1] / 0.002))

    rejilla: dict[tuple[int, int], list[int]] = {}
    for i, r in enumerate(rutas):
        rejilla.setdefault(clave(r["inicio"]), []).append(i)
    fuera = set()
    orden = sorted(
        range(len(rutas)),
        key=lambda i: (-PRIORIDAD_FUENTE.get(rutas[i]["fuente"], 0), rutas[i]["ref"] is None, rutas[i]["id"]),
    )
    for i in orden:
        if i in fuera:
            continue
        a = rutas[i]
        cx, cy = clave(a["inicio"])
        vecinos = [j for dx in (-1, 0, 1) for dy in (-1, 0, 1) for j in rejilla.get((cx + dx, cy + dy), [])]
        # también los que empiezan donde esta acaba (recorrido al revés)
        fx, fy = clave(a["fin"])
        vecinos += [j for dx in (-1, 0, 1) for dy in (-1, 0, 1) for j in rejilla.get((fx + dx, fy + dy), [])]
        for j in set(vecinos):
            if j == i or j in fuera:
                continue
            b = rutas[j]
            if abs(a["km"] - b["km"]) > 0.05 * max(a["km"], b["km"]):
                continue
            d = lambda p, q: metros((p[1], p[0]), (q[1], q[0]))
            mismo = d(a["inicio"], b["inicio"]) < 200 and d(a["fin"], b["fin"]) < 200
            reves = d(a["inicio"], b["fin"]) < 200 and d(a["fin"], b["inicio"]) < 200
            if not (mismo or reves):
                continue
            if a["ref"] and b["ref"] and a["ref"] != b["ref"]:
                continue
            fuera.add(j)
    print(f"      {len(fuera)} rutas duplicadas fuera", flush=True)
    return [r for k, r in enumerate(rutas) if k not in fuera]


SOLO_CODIGO = re.compile(r"^(?:(?:[A-Z]{0,4}[- ]?)?\d+(?:[.,]\d+)?[A-Z]?|\d+[- ]?[A-Z]{1,3})$", re.I)


def nombrar(rutas: list[dict]) -> None:
    """Nombres que se entiendan en una lista:
    - rutas de OSM que solo tienen número o código («19», «R6») → «Sendero 19: Desde – Hasta» o
      «Sendero 19 (provincia)»;
    - tramos de un mismo camino con el mismo nombre (los Caminos Naturales se publican troceados: 69
      «Camino Natural del Ebro») → «…, tramo 3 de 12 en Zaragoza», numerados de oeste a este (o de sur a
      norte si el camino va en esa dirección)."""
    for r in rutas:
        n = r["nombre"] or ""
        if SOLO_CODIGO.match(n.strip()):
            base = n if re.match(r"^[A-Z]", n) else f"Sendero {n}"
            if r.get("desde") and r.get("hasta"):
                r["nombre"] = f"{base}: {r['desde']} – {r['hasta']}"
            else:
                r["nombre"] = f"{base} ({r['provincia']})"
    grupos: dict[str, list[dict]] = {}
    for r in rutas:
        grupos.setdefault(r["nombre"], []).append(r)
    for nombre, rs in grupos.items():
        if len(rs) < 2:
            continue
        por_prov: dict[str, list[dict]] = {}
        for r in rs:
            por_prov.setdefault(r["provincia"], []).append(r)
        for prov, xs in por_prov.items():
            lats = [x["inicio"][0] for x in xs]
            lons = [x["inicio"][1] for x in xs]
            eje = 1 if (max(lons) - min(lons)) >= (max(lats) - min(lats)) else 0
            xs.sort(key=lambda x: x["inicio"][eje])
            for k, x in enumerate(xs, 1):
                sufijo = f"tramo {k} de {len(xs)}" if len(xs) > 1 else ""
                x["nombre"] = f"{nombre} ({', '.join(t for t in (sufijo, prov) if t)})"
