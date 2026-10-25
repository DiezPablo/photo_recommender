"""Eventos del cielo: fases de la luna, lluvias de meteoros, Vía Láctea y eclipses."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from rasante.cielo import astro

TZ = ZoneInfo("Europe/Madrid")
# Centro peninsular: la temporada y las ventanas cambian poco dentro de España (salvo Canarias)
LAT, LON = 40.4, -3.7

# Lluvias de meteoros principales (IMO): fecha del máximo (madrugada de ese día salvo «tarde»),
# THZ (meteoros por hora con el radiante en el cénit y cielo perfecto) y notas para España.
LLUVIAS = [
    ("cuadrantidas", "Cuadrántidas", "01-04", 110, False, "Máximo muy corto (unas horas); radiante alto de madrugada."),
    ("liridas", "Líridas", "04-22", 18, False, "Lluvia modesta pero con bólidos ocasionales; mejor de madrugada."),
    (
        "eta-acuaridas",
        "Eta Acuáridas",
        "05-06",
        50,
        False,
        "Desde España el radiante sale poco antes del alba: pocos meteoros, pero largos.",
    ),
    (
        "perseidas",
        "Perseidas",
        "08-13",
        100,
        False,
        "La más popular: noches templadas y meteoros desde la medianoche hasta el alba.",
    ),
    ("draconidas", "Dracónidas", "10-08", 10, True, "Irregular: casi nada la mayoría de los años; se ve al anochecer."),
    ("orionidas", "Oriónidas", "10-21", 20, False, "Restos del cometa Halley; meteoros rápidos de madrugada."),
    ("leonidas", "Leónidas", "11-17", 15, False, "Meteoros muy rápidos de madrugada."),
    ("geminidas", "Gemínidas", "12-14", 150, False, "La más abundante del año; activa desde las 22 h, noches frías."),
    ("ursidas", "Úrsidas", "12-22", 10, False, "Modesta, cerca del solsticio; radiante circumpolar toda la noche."),
]

# Eclipses visibles desde España (Observatorio Astronómico Nacional / IGN). Solo los grandes de sol.
ECLIPSES = [
    {
        "id": "eclipse-2026-08-12",
        "nombre": "Eclipse total de sol",
        "fecha": "2026-08-12",
        "descripcion": "Total al atardecer en una franja del norte al este peninsular; parcial en el resto.",
        "consejo": "Con el sol muy bajo: un horizonte despejado al oeste es imprescindible.",
    },
    {
        "id": "eclipse-2027-08-02",
        "nombre": "Eclipse total de sol",
        "fecha": "2027-08-02",
        "descripcion": "Total por la mañana (hacia las 10:45) en casi toda la provincia de Cádiz, buena parte de "
        "Málaga, el sur de Granada y Almería, Ceuta y Melilla: hasta 4 min 48 s. Parcial en el resto de España.",
        "consejo": "Filtro solar homologado para todo salvo la totalidad; reserva alojamiento con mucha antelación.",
    },
    {
        "id": "eclipse-2028-01-26",
        "nombre": "Eclipse anular de sol",
        "fecha": "2028-01-26",
        "descripcion": "Anular al atardecer en una franja de suroeste a noreste que cubre casi media España; "
        "parcial en el resto.",
        "consejo": "El anillo de fuego muy cerca del horizonte: busca un primer plano al oeste.",
    },
]
FUENTE_ECLIPSES = "https://visualizadores.ign.es/eclipses/"


def _extremos_iluminacion(desde: date, hasta: date) -> list[tuple[datetime, str]]:
    """Lunas nuevas y llenas: mínimos y máximos de iluminación, a la hora y luego al minuto."""
    t = datetime(desde.year, desde.month, desde.day, tzinfo=UTC) - timedelta(hours=1)
    fin = datetime(hasta.year, hasta.month, hasta.day, tzinfo=UTC) + timedelta(days=1)
    paso = timedelta(hours=1)
    previo, actual = astro.iluminacion_luna(t - paso), astro.iluminacion_luna(t)
    fases = []
    while t < fin:
        siguiente = astro.iluminacion_luna(t + paso)
        es_max = actual >= previo and actual > siguiente
        es_min = actual <= previo and actual < siguiente
        if es_max or es_min:
            signo = 1 if es_max else -1
            mejor = max(
                (t + timedelta(minutes=m) for m in range(-60, 61)),
                key=lambda x: signo * astro.iluminacion_luna(x),
            )
            fases.append((mejor, "llena" if es_max else "nueva"))
        t, previo, actual = t + paso, actual, siguiente
    return [(m, f) for m, f in fases if desde <= m.astimezone(TZ).date() <= hasta]


def fases_luna(desde: date, hasta: date) -> list[dict]:
    """Lunas nuevas y llenas entre dos fechas (fecha y hora local de España peninsular)."""
    return [
        {"fecha": m.astimezone(TZ).date().isoformat(), "hora": m.astimezone(TZ).strftime("%H:%M"), "fase": f}
        for m, f in _extremos_iluminacion(desde, hasta)
    ]


def _luna_en(t: datetime) -> dict:
    return {
        "iluminacion": round(astro.iluminacion_luna(t) * 100),
        "arriba": astro.altura_luna(LAT, LON, t) > 0,
    }


def lluvias_meteoros(desde: date, hasta: date) -> list[dict]:
    """Máximos de las lluvias de meteoros entre dos fechas, con la luna que habrá esa noche."""
    eventos = []
    for anio in range(desde.year, hasta.year + 1):
        for id_, nombre, md, thz, tarde, nota in LLUVIAS:
            mes, dia = (int(x) for x in md.split("-"))
            fecha = date(anio, mes, dia)
            if not desde <= fecha <= hasta:
                continue
            # la hora de observación: madrugada (4 h) o anochecer (22 h del día del máximo)
            local = datetime(anio, mes, dia, 22 if tarde else 4, tzinfo=TZ)
            luna = _luna_en(local)
            molesta = luna["arriba"] and luna["iluminacion"] >= 40
            eventos.append(
                {
                    "id": f"{id_}-{anio}",
                    "nombre": nombre,
                    "tipo": "meteoros",
                    "fecha": fecha.isoformat(),
                    "noche": (fecha - timedelta(days=0 if tarde else 1)).isoformat(),
                    "thz": thz,
                    "luna": luna,
                    "calidad": "mala" if molesta else ("regular" if luna["iluminacion"] >= 40 else "buena"),
                    "descripcion": nota,
                }
            )
    return eventos


def via_lactea(desde: date, hasta: date) -> dict:
    """Temporada del núcleo (horas por noche a mitad de cada mes) y ventanas sin luna alrededor de cada
    luna nueva: noches seguidas con al menos 1 h de núcleo alto, noche cerrada y sin luna."""
    meses = []
    for i in range(12):
        n = astro.calcular_noche(LAT, LON, date(2027, i + 1, 15), TZ)
        meses.append(round(n.vl_horas, 1))
    ventanas = []
    for nueva in (f for f in fases_luna(desde, hasta) if f["fase"] == "nueva"):
        centro = date.fromisoformat(nueva["fecha"])
        noches = []
        for d in range(-6, 7):
            dia = centro + timedelta(days=d)
            n = astro.calcular_noche(LAT, LON, dia, TZ)
            if n.vl_horas_sin_luna >= 1:
                noches.append((dia, n.vl_horas_sin_luna))
        if noches:
            mejor = max(noches, key=lambda x: x[1])
            ventanas.append(
                {
                    "desde": noches[0][0].isoformat(),
                    "hasta": noches[-1][0].isoformat(),
                    "luna_nueva": nueva["fecha"],
                    "horas_max": round(mejor[1], 1),
                }
            )
    return {"horas_por_mes": meses, "ventanas": ventanas}


def eclipses(desde: date) -> list[dict]:
    """Todos los eclipses futuros: merece la pena verlos con años de antelación."""
    return [
        {**e, "tipo": "eclipse", "fuente": FUENTE_ECLIPSES} for e in ECLIPSES if date.fromisoformat(e["fecha"]) >= desde
    ]
