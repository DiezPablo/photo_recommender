"""Historial de previsiones y observaciones (60 días) y aciertos de los últimos 30 con la previsión del día
anterior. Para que el número signifique algo se compara con no saber nada: repetir lo observado el día antes
(persistencia)."""

from __future__ import annotations

from datetime import date, timedelta

from rasante.verificacion.criterios import HORAS_NOCHE

DIAS_HISTORIAL = 60
DIAS_MARCADOR = 30
UMBRAL_NIEBLA = 0.3


def fusionar(historial: dict, previsiones: list[dict], observaciones: list[dict], hoy: date) -> dict:
    limite = (hoy - timedelta(days=DIAS_HISTORIAL)).isoformat()
    prev = {(p["emitida"], p["oaci"], p["fecha"]): p for p in historial.get("previsiones", []) + previsiones}
    obs = {(o["oaci"], o["fecha"]): o for o in historial.get("observaciones", []) + observaciones}
    return {
        "previsiones": sorted(
            (p for p in prev.values() if p["fecha"] >= limite), key=lambda p: (p["fecha"], p["oaci"])
        ),
        "observaciones": sorted(
            (o for o in obs.values() if o["fecha"] >= limite), key=lambda o: (o["fecha"], o["oaci"])
        ),
    }


def _pct(a: int, b: int) -> int | None:
    return round(100 * a / b) if b else None


def marcador(historial: dict, hoy: date) -> dict:
    desde = (hoy - timedelta(days=DIAS_MARCADOR)).isoformat()
    obs = {(o["oaci"], o["fecha"]): o for o in historial["observaciones"]}
    pares = []
    for p in historial["previsiones"]:
        # la previsión emitida el día anterior para ese día
        if p["fecha"] < desde or (date.fromisoformat(p["fecha"]) - date.fromisoformat(p["emitida"])).days != 1:
            continue
        o = obs.get((p["oaci"], p["fecha"]))
        ayer = obs.get((p["oaci"], (date.fromisoformat(p["fecha"]) - timedelta(days=1)).isoformat()))
        if o:
            pares.append((p, o, ayer))
    n = len(pares)
    nieblas = [(p, o) for p, o, _ in pares if o["niebla"]]
    avisos = [(p, o) for p, o, _ in pares if p["niebla"] >= UMBRAL_NIEBLA]
    acierto_cub = sum(p["cubierto"] == o["cubierto"] for p, o, _ in pares)
    pers_cub = [(o, a) for _, o, a in pares if a]
    noche = lambda h: h >= HORAS_NOCHE
    acierto_noc = sum(noche(p["despejadas"]) == noche(o["despejadas"]) for p, o, _ in pares)
    return {
        "desde": desde,
        "hasta": hoy.isoformat(),
        "casos": n,
        "aeropuertos": len({p["oaci"] for p, _, _ in pares}),
        "niebla": {
            "observadas": len(nieblas),
            "detectadas": sum(p["niebla"] >= UMBRAL_NIEBLA for p, _ in nieblas),
            "avisos": len(avisos),
            "avisos_acertados": sum(o["niebla"] for _, o in avisos),
            "umbral": UMBRAL_NIEBLA,
        },
        "atardecer_cubierto": {
            "acierto": _pct(acierto_cub, n),
            "persistencia": _pct(sum(o["cubierto"] == a["cubierto"] for o, a in pers_cub), len(pers_cub)),
        },
        "noche_despejada": {
            "acierto": _pct(acierto_noc, n),
            "persistencia": _pct(
                sum(noche(o["despejadas"]) == noche(a["despejadas"]) for o, a in pers_cub), len(pers_cub)
            ),
        },
    }
