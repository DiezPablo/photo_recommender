"""Evaluación de cada spot y día: sol, luna y Vía Láctea, meteo en el pico de color y a lo largo del camino
de la luz, perfil vertical para la niebla, y las cinco notas con su desglose y confianza."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from rasante.cielo import astro
from rasante.cielo.contaminacion import contaminacion, cupula
from rasante.notas import KM_CAMINO, capa_nubosa, nota_astro, nota_luna, nota_luz, nota_niebla, valor
from rasante.terreno import horizonte

from . import mar, openmeteo, series
from .openmeteo import AIRE_URL, MODELO_ALT, VARS_ALT, VARS_CAMINO, VARS_PERFIL, VARS_SPOT, pedir
from .series import en, filas_entre, perfil_en, suma_entre

# Rejillas (grados) para compartir peticiones entre spots: lejos del spot basta una rejilla gruesa
REDONDEO_SPOT = 0.05


REDONDEO_CAMINO = {15: 0.1, 40: 0.25, 80: 0.25, 150: 0.5}


REDONDEO_PERFIL = 0.5


REDONDEO_ALT = 0.25  # ECMWF IFS tiene 0,25° de resolución: más fino no aporta


KM_PERFIL = 40  # el perfil vertical se toma en el llano, en los puntos a 40 km


MIN_PICO = 15  # el color es máximo ~15 min antes de salir el sol / después de ponerse


DIAS_POR_DEFECTO = 5


TIPOS_AGUA = {"lago", "embalse", "playa", "cascada", "río", "costa"}


def fiabilidad(indice_dia: int) -> str:
    """La nubosidad prevista pierde mucha precisión a partir del tercer día."""
    return "alta" if indice_dia <= 1 else "media" if indice_dia == 2 else "baja"


def _hhmm(t: datetime | None) -> str | None:
    return t.strftime("%H:%M") if t else None


def _tramo(par) -> list[str] | None:
    return [_hhmm(par[0]), _hhmm(par[1])] if par else None


def _r(x, n=0):
    if x is None:
        return None
    return round(x, n) if n else round(x)


def _redondear(c: tuple[float, float], paso: float) -> tuple[float, float]:
    return (round(round(c[0] / paso) * paso, 4), round(round(c[1] / paso) * paso, 4))


def _meteo_momento(f: dict, camino: list[dict], aire: dict) -> dict:
    return {
        "nubes_bajas": _r(valor(f, "cloud_cover_low")),
        "nubes_medias": _r(valor(f, "cloud_cover_mid")),
        "nubes_altas": _r(valor(f, "cloud_cover_high")),
        "nubes_horizonte": _r(max((valor(p, "low") for p in camino), default=0)),
        "camino": [{"km": p["km"], "bajas": _r(valor(p, "low"))} for p in camino],
        "visibilidad_km": _r(valor(f, "visibility", 24000) / 1000, 1),
        "lluvia": _r(valor(f, "precipitation_probability")),
        "viento": _r(valor(f, "wind_speed_10m")),
        "temperatura": _r(valor(f, "temperature_2m"), 1),
        "humedad": _r(valor(f, "relative_humidity_2m")),
        "aod": aire.get("aod"),
        "polvo": aire.get("polvo"),
    }


def _confianza(nota: float, alternativa: float | None) -> str | None:
    if alternativa is None:
        return None
    d = abs(nota - alternativa)
    return "alta" if d < 1.5 else "media" if d < 3 else "baja"


def _aire_en(aq: pd.DataFrame | None, t: datetime) -> dict:
    f = en(aq, t)
    aod, polvo = f.get("aerosol_optical_depth"), f.get("dust")
    return {
        "aod": None if aod is None or pd.isna(aod) else round(float(aod), 2),
        "polvo": None if polvo is None or pd.isna(polvo) else round(float(polvo)),
    }


def zona_de(lon: float, defecto: ZoneInfo) -> ZoneInfo:
    """Canarias va una hora por detrás de la península: sus horas se dan en su hora local."""
    return ZoneInfo("Atlantic/Canary") if lon < -12 else defecto


def evaluar_spot_dia(spot: dict, dia: date, indice: int, tz: ZoneInfo, datos: dict) -> dict:
    """datos: {"spot": df, "elevacion", "camino": {momento: [(km, df)]}, "perfil": [(df, elevación)],
    "alt": df, "aire": df}."""
    df, alt, aq = datos["spot"], datos.get("alt"), datos.get("aire")
    perfil_relieve = spot.get("relieve")
    hz = (lambda az: horizonte.angulo(perfil_relieve, az) or 0.0) if perfil_relieve else None
    sol = astro.calcular_sol(spot["lat"], spot["lon"], dia, tz)
    noche = astro.calcular_noche(spot["lat"], spot["lon"], dia, tz, sol, horizonte=hz)
    relieve = {}
    if hz:
        for m in ("amanecer", "atardecer"):
            hora_r, ang = astro.sol_sobre_relieve(spot["lat"], spot["lon"], dia, tz, hz, m)
            relieve[m] = (hora_r, ang)
    es_agua = (spot.get("tipo") or "") in TIPOS_AGUA
    notas, meteo, avisos = {}, {}, []

    # ---- amanecer y atardecer, en el pico de color
    for momento, hora, signo in (("amanecer", sol.amanecer, -1), ("atardecer", sol.atardecer, 1)):
        if hora is None:
            continue
        t = hora + timedelta(minutes=signo * MIN_PICO)
        f = en(df, t)
        camino = []
        for km, h in datos["camino"].get(momento, []):
            fc = en(h, t)
            camino.append(
                {
                    "km": km,
                    "low": valor(fc, "cloud_cover_low"),
                    "mid": valor(fc, "cloud_cover_mid"),
                    "high": valor(fc, "cloud_cover_high"),
                }
            )
        aire = _aire_en(aq, t)
        aire["lluvia_previa_mm"] = suma_entre(df, "precipitation", t - timedelta(hours=24), t - timedelta(hours=1))
        h_rel, ang_rel = relieve.get(momento, (None, None))
        kw_rel = {"relieve": ang_rel, "hora_relieve": _hhmm(h_rel)}
        n = nota_luz(f, camino, aire, es_agua=es_agua, momento=momento, **kw_rel)
        d = n.a_dict()
        if alt is not None:
            fa = {**f, **{k: v for k, v in en(alt, t).items() if k in VARS_ALT}}
            d["confianza"] = _confianza(n.valor, nota_luz(fa, camino, aire, es_agua, momento, **kw_rel).valor)
        notas[momento] = d
        meteo[momento] = _meteo_momento(f, camino, aire)

    # ---- noche
    lp = spot.get("contaminacion") or {}
    if noche.ini and noche.fin:
        horas, horas_alt = [], []
        t = noche.ini
        while t < noche.fin:
            luna = noche.luna_iluminacion if astro.altura_luna(spot["lat"], spot["lon"], t) > 0 else 0.0
            horas.append({"t": _hhmm(t), "nubes": valor(en(df, t), "cloud_cover", 100), "luna": luna})
            if alt is not None:
                horas_alt.append({"t": _hhmm(t), "nubes": valor(en(alt, t), "cloud_cover", 100), "luna": luna})
            t += timedelta(hours=1)
        toda = filas_entre(df, noche.ini, noche.fin)
        margen = float((toda["temperature_2m"] - toda["dew_point_2m"]).min()) if not toda.empty else 99.0
        mitad = noche.ini + (noche.fin - noche.ini) / 2
        aire_noche = _aire_en(aq, mitad)
        hacia_nucleo = noche.vl_azimut_max is not None
        try:
            cup = cupula(spot["lat"], spot["lon"], noche.vl_azimut_max if hacia_nucleo else 180.0)
        except requests.RequestException:
            cup = None
        if cup:
            cup["hacia"] = "el núcleo de la Vía Láctea" if hacia_nucleo else "el sur"
        perfiles = [p for p, _ in datos.get("perfil", []) if p is not None]
        vapor = en(perfiles[0], mitad).get("total_column_integrated_water_vapour") if perfiles else None
        args = dict(
            sqm=lp.get("sqm"),
            zona_lp=lp.get("zona"),
            cupula=cup,
            vapor_mm=None if vapor is None or pd.isna(vapor) else float(vapor),
            aod=aire_noche["aod"],
            elevacion=datos.get("elevacion"),
            vl_horas_sin_luna=noche.vl_horas_sin_luna,
            vl_altura_max=noche.vl_altura_max,
            margen_rocio=margen,
            rachas=float(toda["wind_gusts_10m"].max()) if not toda.empty else 0.0,
            humedad=float(toda["relative_humidity_2m"].mean()) if not toda.empty else 60.0,
        )
        n = nota_astro(horas, **args)
        d = n.a_dict()
        if horas_alt:
            d["confianza"] = _confianza(n.valor, nota_astro(horas_alt, **args).valor)
        notas["astro"] = d
        meteo["noche"] = {
            "nubes": _r(sum(h["nubes"] for h in horas) / len(horas)) if horas else None,
            "humedad": _r(args["humedad"]),
            "viento": _r(float(toda["wind_speed_10m"].mean())) if not toda.empty else None,
            "rachas": _r(args["rachas"]),
            "temp_min": _r(float(toda["temperature_2m"].min()), 1) if not toda.empty else None,
            "punto_rocio": _r(float(toda["dew_point_2m"].max()), 1) if not toda.empty else None,
            "margen_rocio": _r(margen, 1),
            "vapor_mm": _r(args["vapor_mm"]),
            "aod": aire_noche["aod"],
            "cupula": cup,
            "horas": [{"t": h["t"], "nubes": _r(h["nubes"]), "luna": round(h["luna"], 2)} for h in horas],
        }
    else:
        notas["astro"] = nota_astro([], None).a_dict()

    # ---- luna sobre el paisaje en el crepúsculo
    ev = astro.evento_luna(spot["lat"], spot["lon"], dia, tz, sol, hz)
    evento = None
    if ev:
        evento = {
            "tipo": ev.tipo,
            "hora": _hhmm(ev.hora),
            "azimut": round(ev.azimut),
            "horizonte": round(ev.horizonte, 1),
            "iluminacion": round(ev.iluminacion, 2),
            "altura_sol": round(ev.altura_sol, 1),
        }
        lado = (
            "amanecer" if ev.tipo == "salida" else "atardecer"
        )  # la luna llena sale por el este y se pone por el oeste
        cam_luna = [
            {"km": km, "low": valor(en(h, ev.hora), "cloud_cover_low")} for km, h in datos["camino"].get(lado, [])
        ]
        notas["luna"] = nota_luna(evento, en(df, ev.hora), cam_luna).a_dict()
        if alt is not None:
            fa = {**en(df, ev.hora), **{k: v for k, v in en(alt, ev.hora).items() if k in VARS_ALT}}
            notas["luna"]["confianza"] = _confianza(notas["luna"]["nota"], nota_luna(evento, fa, cam_luna).valor)
    else:
        notas["luna"] = nota_luna(None).a_dict()

    # ---- niebla y mar de nubes, al amanecer
    if sol.amanecer:
        madrugada = filas_entre(df, sol.amanecer - timedelta(hours=3), sol.amanecer + timedelta(hours=1))
        capas = [
            c for c in (capa_nubosa(perfil_en(p, sol.amanecer, suelo)) for p, suelo in datos.get("perfil", [])) if c
        ]
        capa = max(capas, key=lambda c: c["cobertura"]) if capas else None
        n = nota_niebla(
            madrugada.to_dict("records"),
            datos.get("elevacion"),
            capa,
            spot.get("tipo"),
            valor(en(df, sol.amanecer), "cloud_cover_low"),
        )
        notas["niebla"] = n.a_dict()
        if capa:
            meteo["capa_nubosa"] = {
                "techo": _r(capa["techo"]),
                "cobertura": _r(capa["cobertura"]),
                "inversion": _r(capa["inversion"], 1),
            }

    for n in notas.values():
        avisos += [a for a in n["avisos"] if a not in avisos]

    return {
        "fecha": dia.isoformat(),
        "fiabilidad": fiabilidad(indice),
        "sol": {
            "amanecer": _hhmm(sol.amanecer),
            "atardecer": _hhmm(sol.atardecer),
            "amanecer_relieve": _hhmm(relieve.get("amanecer", (None,))[0]),
            "atardecer_relieve": _hhmm(relieve.get("atardecer", (None,))[0]),
            "relieve_amanecer": _r(relieve.get("amanecer", (None, None))[1], 1),
            "relieve_atardecer": _r(relieve.get("atardecer", (None, None))[1], 1),
            "az_amanecer": _r(sol.az_amanecer),
            "az_atardecer": _r(sol.az_atardecer),
            "dorada_manana": _tramo(sol.dorada_manana),
            "dorada_tarde": _tramo(sol.dorada_tarde),
            "azul_manana": _tramo(sol.azul_manana),
            "azul_tarde": _tramo(sol.azul_tarde),
        },
        "noche": {
            "ini": _hhmm(noche.ini),
            "fin": _hhmm(noche.fin),
            "horas": _r(noche.horas_oscuras, 1),
            "luna": {
                "fase": noche.luna_fase,
                "iluminacion": _r(noche.luna_iluminacion * 100),
                "edad": _r(noche.luna_edad, 1),
                "salida": _hhmm(noche.luna_salida),
                "puesta": _hhmm(noche.luna_puesta),
                "sin_luna": [_tramo(t) for t in noche.sin_luna],
                "evento": evento,
                "horas_sin_luna": _r(noche.horas_sin_luna, 1),
            },
            "via_lactea": {
                "tramos": [_tramo(t) for t in noche.vl_tramos],
                "horas": _r(noche.vl_horas, 1),
                "horas_sin_luna": _r(noche.vl_horas_sin_luna, 1),
                "altura_max": _r(noche.vl_altura_max),
                "azimut_max": _r(noche.vl_azimut_max),
                "hora_max": _hhmm(noche.vl_hora_max),
                "azimut_ini": _r(noche.vl_azimut_ini),
                "azimut_fin": _r(noche.vl_azimut_fin),
            },
        },
        "meteo": meteo,
        "notas": notas,
        "avisos": avisos,
    }


def planificar(spots: list[dict], dia0: date, tz: ZoneInfo) -> tuple[dict, list[dict]]:
    """Qué puntos pedir y a qué spot sirve cada uno. El azimut del sol cambia menos de 1° al día:
    se usa el del primer día para todo el informe."""
    puntos: dict[str, dict[tuple[float, float], int]] = {"spot": {}, "camino": {}, "perfil": {}, "alt": {}}

    def indice(tipo, c):
        return puntos[tipo].setdefault(c, len(puntos[tipo]))

    planes = []
    for s in spots:
        sol0 = astro.calcular_sol(s["lat"], s["lon"], dia0, tz)
        plan = {
            "spot": indice("spot", _redondear((s["lat"], s["lon"]), REDONDEO_SPOT)),
            "camino": {},
            "perfil": [],
            "horizonte": {},
            "alt": indice("alt", _redondear((s["lat"], s["lon"]), REDONDEO_ALT)),
        }
        for momento, az in (("amanecer", sol0.az_amanecer), ("atardecer", sol0.az_atardecer)):
            if az is None:
                continue
            plan["camino"][momento] = []
            for km in KM_CAMINO:
                c = _redondear(astro.punto_destino(s["lat"], s["lon"], az, km), REDONDEO_CAMINO[km])
                plan["camino"][momento].append((km, indice("camino", c)))
                if km == KM_PERFIL:
                    plan["perfil"].append(indice("perfil", _redondear(c, REDONDEO_PERFIL)))
                    plan["horizonte"][momento] = list(c)
        planes.append(plan)
    return puntos, planes


def pedir_todo(puntos: dict, dias: int, tz_nombre: str) -> dict:
    c_spot, c_camino, c_perfil, c_alt = (list(puntos[k]) for k in ("spot", "camino", "perfil", "alt"))
    print(
        f"  Open-Meteo: {len(c_spot)} celdas de spots, {len(c_camino)} puntos del camino del sol, "
        f"{len(c_perfil)} perfiles verticales, {len(c_alt)} celdas del segundo modelo"
    )
    prev = {
        "spot": pedir(c_spot, VARS_SPOT, dias, tz_nombre, extra={"past_days": 2}),
        "camino": pedir(c_camino, VARS_CAMINO, dias, tz_nombre),
        "perfil": pedir(c_perfil, VARS_PERFIL, dias, tz_nombre),
        "alt": pedir(c_alt, VARS_ALT, dias, tz_nombre, extra={"models": MODELO_ALT}, obligatorio=False),
    }
    # Aerosoles y polvo (CAMS): rejilla de 0,4°, basta un punto por celda
    celdas = sorted({_redondear(c, 0.4) for c in c_spot})
    aire = pedir(celdas, ["aerosol_optical_depth", "dust"], min(dias, 4), tz_nombre, url=AIRE_URL, obligatorio=False)
    por_celda = dict(zip(celdas, aire, strict=True))
    prev["aire"] = [por_celda.get(_redondear(c, 0.4)) for c in c_spot]
    print(f"  ≈ {openmeteo.LLAMADAS['total']:.0f} llamadas a Open-Meteo en esta ejecución")
    return prev


def pedir_mar(spots: list[dict], dias: int, tz_nombre: str) -> dict:
    """Serie del mar (mareas y oleaje) de los spots de costa, por id. Opcional: si falla, sin mar."""
    costa = mar.Costa()
    costeros = [s for s in spots if costa.es_costero(s)]
    celdas = sorted({_redondear((s["lat"], s["lon"]), mar.REDONDEO) for s in costeros})
    print(f"  Open-Meteo Marine: {len(costeros)} spots de costa en {len(celdas)} celdas")
    por_celda = dict(zip(celdas, mar.pedir_mar(celdas, dias, tz_nombre), strict=True))
    salida = {}
    for s in costeros:
        x = por_celda.get(_redondear((s["lat"], s["lon"]), mar.REDONDEO))
        if x is not None:
            salida[s["id"]] = x["horas"]
    return salida


def evaluar(
    spots: list[dict], dias: int, tz_nombre: str, hoy: date | None = None, previsiones: dict | None = None
) -> dict:
    """previsiones (para tests): {"spot": [...], "camino": [...], "perfil": [...], "alt": [...],
    "aire": [...]} con el formato de pedir(), en el orden de planificar()."""
    tz = ZoneInfo(tz_nombre)
    series.ZONA_SERIES = tz
    hoy = hoy or datetime.now(tz).date()
    fechas = [hoy + timedelta(days=i) for i in range(dias)]

    for s in spots:
        if s.get("contaminacion") is None:
            try:
                s["contaminacion"] = contaminacion(s["lat"], s["lon"])
            except requests.RequestException as e:
                print(f"  sin atlas de contaminación para {s['nombre']}: {e}")

    puntos, planes = planificar(spots, fechas[0], tz)
    if previsiones is None:
        previsiones = pedir_todo(puntos, dias, tz_nombre)
        previsiones["mar"] = pedir_mar(spots, dias, tz_nombre)

    def horas(lista, i):
        x = lista[i] if lista and i < len(lista) else None
        return x["horas"] if x else None

    salida = []
    for s, plan in zip(spots, planes, strict=True):
        p = previsiones["spot"][plan["spot"]]
        datos = {
            "spot": p["horas"],
            "elevacion": p["elevacion"],
            "camino": {
                m: [(km, horas(previsiones["camino"], i)) for km, i in pts] for m, pts in plan["camino"].items()
            },
            "perfil": [
                (horas(previsiones["perfil"], i), (previsiones["perfil"][i] or {}).get("elevacion"))
                for i in plan["perfil"]
            ],
            "alt": horas(previsiones.get("alt"), plan["alt"]),
            "aire": horas(previsiones.get("aire"), plan["spot"]),
        }
        tz_spot = zona_de(s["lon"], tz)
        dias_spot = [evaluar_spot_dia(s, d, i, tz_spot, datos) for i, d in enumerate(fechas)]
        if (serie_mar := (previsiones.get("mar") or {}).get(s["id"])) is not None:
            for d, dia_spot in zip(fechas, dias_spot, strict=True):
                sol = astro.calcular_sol(s["lat"], s["lon"], d, tz_spot)
                momentos = {
                    "amanecer": sol.amanecer and sol.amanecer - timedelta(minutes=MIN_PICO),
                    "atardecer": sol.atardecer and sol.atardecer + timedelta(minutes=MIN_PICO),
                }
                if (m := mar.dia(serie_mar, d, tz_spot, momentos)) is not None:
                    dia_spot["mar"] = m
        salida.append(
            {
                "id": s["id"],
                "nombre": s["nombre"],
                "lat": round(s["lat"], 5),
                "lon": round(s["lon"], 5),
                "tipo": s.get("tipo"),
                "origen": s.get("origen"),
                "elevacion": _r((s.get("relieve") or {}).get("elevacion") or p["elevacion"]),
                "provincia": s.get("provincia"),
                "ccaa": s.get("ccaa"),
                "contaminacion": s.get("contaminacion"),
                "horizonte": plan["horizonte"],
                "zona_horaria": tz_spot.key,
                "dias": dias_spot,
            }
        )
    return {
        "generado": datetime.now(tz).isoformat(timespec="minutes"),
        "zona_horaria": tz_nombre,
        "modelo": "v2",
        "fechas": [f.isoformat() for f in fechas],
        "fuentes": {
            "tiempo": "Open-Meteo (open-meteo.com), CC BY 4.0; segundo modelo: ECMWF IFS",
            "aire": "CAMS vía Open-Meteo Air Quality",
            "contaminacion": "World Atlas of Artificial Night Sky Brightness 2025, D. Lorenz (VIIRS)",
            "mapa": "© colaboradores de OpenStreetMap (ODbL)",
            "fotos": "Wikimedia Commons (autor y licencia en cada foto)",
        },
        "spots": salida,
    }


def mejores(informe: dict, fecha: str, n: int = 5) -> list[tuple[float, str, str]]:
    filas = []
    for s in informe["spots"]:
        for d in s["dias"]:
            if d["fecha"] == fecha:
                filas += [(v["nota"], k, s["nombre"]) for k, v in d["notas"].items()]
    return sorted(filas, reverse=True)[:n]
