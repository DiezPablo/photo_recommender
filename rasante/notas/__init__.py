"""
Modelos de predicción: nota 0-10 por tipo de salida, con desglose explicable.

Versión 2 (oct-2026), basada en lo que miden los servicios especializados y lo que repiten los
fotógrafos (fuentes en registro.md):

- Amanecer/atardecer: modelo de **camino de la luz** (como Sunsethue): para que las nubes se
  enciendan hace falta (1) un lienzo de nubes medias/altas sobre el observador y hacia el sol,
  (2) que la luz del sol llegue a ellas: sin nubes bajas a lo largo de su camino (15-150 km hacia
  el sol), (3) que las nubes bajas locales no tapen el lienzo y (4) aire limpio (aerosoles, polvo
  y humedad apagan el color; tras la lluvia el aire está lavado). Se evalúa en el pico de color:
  15 min antes de salir el sol / 15 min después de ponerse.
- Noche: calidad hora a hora (oscuridad × cielo despejado) y se queda la **mejor ventana de 3 h**,
  multiplicada por la transparencia (vapor de agua, aerosoles, humedad) y la contaminación lumínica
  local y la **cúpula de luz hacia donde se mira** (núcleo de la Vía Láctea o el sur).
- Niebla: probabilidad calibrada con 10 años de METAR de los aeropuertos de Madrid (humedad máxima
  y viento mínimo de madrugada) y **mar de nubes** con el perfil vertical real (techo de la capa
  nubosa en el llano y altura del spot).

Las notas son sumas de factores con nombre: cada factor muestra cuánto cambia la nota, de modo que
el desglose de la web suma exactamente la nota (antes del recorte a 0-10).
"""

from .base import Acumulador, Nota, clamp, por_tramos, valor
from .luna import nota_luna
from .luz import (
    KM_CAMINO,
    PESO_CAMINO,
    PESO_MEDIAS,
    calidad_lienzo,
    claridad_aire,
    lienzo,
    nota_luz,
    transmision_camino,
)
from .niebla import CALIBRACION_NIEBLA, TIPOS_NIEBLA, TIPOS_VISTA, capa_nubosa, nota_niebla, prob_niebla_radiacion
from .noche import factor_sqm, factor_transparencia, nota_astro

__all__ = [
    "CALIBRACION_NIEBLA",
    "KM_CAMINO",
    "PESO_CAMINO",
    "PESO_MEDIAS",
    "TIPOS_NIEBLA",
    "TIPOS_VISTA",
    "Acumulador",
    "Nota",
    "calidad_lienzo",
    "capa_nubosa",
    "clamp",
    "claridad_aire",
    "factor_sqm",
    "factor_transparencia",
    "lienzo",
    "nota_astro",
    "nota_luna",
    "nota_luz",
    "nota_niebla",
    "por_tramos",
    "prob_niebla_radiacion",
    "transmision_camino",
    "valor",
]
