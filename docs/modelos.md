# Modelos de puntuación

Cada nota es una **suma de factores con nombre**: la web muestra el desglose y suma exactamente la nota
(antes de recortarla a 0-10). Código en [`rasante/notas/`](../rasante/notas/); casos de prueba en
[`tests/test_puntuacion.py`](../tests/test_puntuacion.py). La explicación para el usuario está en la página
*Método* de la web (`src/app/acerca/page.tsx`).

> Antes de cambiar pesos, mira el informe de validación (workflow *Validar notas*, artefacto `validacion`)
> y no ajustes más allá del ruido.

## Amanecer y atardecer: el camino de la luz (`notas/luz.py`)

Se evalúa en el **pico de color**: 15 min antes de salir el sol y 15 min después de ponerse (interpolado).

| Factor | Qué mide |
|---|---|
| Base 3 | Luz rasante del sol, si llega |
| Lienzo (hasta +7) | Nubes altas y medias sobre el spot (60 %) y a 15-40 km hacia el sol (40 %). Ideal 40-70 %. Las medias cuentan la mitad (`PESO_MEDIAS`, validado) |
| Camino del sol | Nubes bajas a 15, 40, 80 y 150 km en la dirección del sol (`PESO_CAMINO`): un banco a 30-50 km apaga el cielo |
| Nubes bajas locales | Tapan el lienzo |
| Aire | Aerosoles y calima (CAMS), humedad; tras la lluvia, aire lavado |
| Relieve | Si una montaña tapa el sol, se esconde antes y se pierde la luz rasante |
| Otros | Lluvia, visibilidad, reflejos en el agua sin viento |

Confianza: la misma nota con las nubes de un segundo modelo (ECMWF IFS). Si difieren mucho, «previsión dudosa».

## Noche y Vía Láctea (`notas/noche.py`)

Calidad hora a hora (oscuridad × cielo despejado) y se queda la **mejor ventana de 3 h**, multiplicada por la
transparencia (vapor de agua en columna, aerosoles, humedad) y la contaminación lumínica: la del spot (atlas de
D. Lorenz 2025) y la cúpula de luz hacia donde se mira (núcleo de la Vía Láctea o el sur). Suma si el núcleo
está alto sin luna; restan las rachas de viento; aviso de rocío.

## Niebla y mar de nubes (`notas/niebla.py`)

- **Niebla de radiación**: probabilidad calibrada (`CALIBRACION_NIEBLA`) con 11 792 madrugadas de METAR de los
  aeropuertos de Madrid (2016-2025). Lo que la anuncia es la humedad máxima de madrugada (rampa del 85 al
  100 %) y el viento mínimo (aguanta hasta ~6 km/h, desaparece hacia 20). Si el modelo prevé visibilidad
  < 1 km con humedad ≥ 90 %, es evidencia directa.
- **Mar de nubes**: con el perfil vertical (niveles de presión) en el llano se calcula el techo de la capa de
  nubes bajas y la inversión; si el spot queda encima, es candidato.
- Fotogénica en embalses, lagos, ríos o bosques; en miradores y cumbres significa estar dentro de la nube.

## Luna (`notas/luna.py`)

La luna grande saliendo o poniéndose en el crepúsculo: casi llena, sobre el relieve, con el sol entre 6° bajo
el horizonte y 2° sobre él, y sin nubes bajas en su dirección.

## Rutas (`rutas/metricas.py`)

No es una nota, pero sigue el mismo principio de transparencia:
- **Desnivel** con el DEM a ~30 m, suavizado (5 puntos) e histéresis de 3 m.
- **Tiempo** por el método MIDE: 4 km/h en llano, 400 m/h subiendo, 600 m/h bajando; el mayor de horizontal
  y vertical más la mitad del menor. Sin paradas. Más de 12 h se muestra en jornadas de ~7 h.
- **Esfuerzo** estimado con tiempo, desnivel y altitud. No es la valoración MIDE oficial.

## Validación (`rasante/validacion/`)

| Qué | Cómo | Resultado |
|---|---|---|
| Sol, luna, Vía Láctea | Contra USNO y astropy (`tests/test_astro.py`) | Minutos y décimas de grado |
| Niebla | 11 792 madrugadas con METAR (Barajas, Getafe, Cuatro Vientos, Torrejón) | AUC 0,92 |
| Amanecer y atardecer | Días con fotos de puestas y salidas en Commons (fecha EXIF) frente al resto del mismo mes, con ERA5 | AUC 0,60 (v1: 0,56); amanecer 0,66 |

El AUC es la probabilidad de que un día positivo puntúe más que uno cualquiera del mismo mes (0,5 = azar).
La señal de Commons es ruidosa: también se fotografían puestas mediocres y muchas buenas no se suben.
