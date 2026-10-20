# Registro de decisiones y problemas

Diario de trabajo del encargo (`ENCARGO.md`). Lo más reciente, abajo.

## 2026-10-19/20 · Arranque

### Entorno
- **Commons responde 429 desde el contenedor de desarrollo** (IP de salida compartida;
  `retry-after` de 30-50 s). Con el `curl` por defecto ni siquiera contesta: exige un User-Agent
  descriptivo. *Solución*: User-Agent con URL del proyecto, `Retry-After` respetado, pausa de 1 s
  entre peticiones, reintentos también ante `"Search is currently too busy"`, y el
  descubrimiento real corre en GitHub Actions, con la caché de respuestas guardada entre ejecuciones
  (`actions/cache`).
- **overpass-api.de corta la conexión** desde el contenedor. *Solución*: lista de espejos
  (`overpass-api.de` → `overpass.openstreetmap.fr` → `overpass.kumi.systems`), se prueba el siguiente
  si uno falla.
- Open-Meteo da algún `SSLError` puntual a través del proxy: reintentos también ante errores de conexión.

### Decisiones
- **Astronomía** (`astro.py`): astral para sol, salida y puesta de la luna; iluminación lunar con la
  fórmula de Meeus (cap. 48); centro galáctico con tiempo sidéreo y precesión rigurosa (Meeus cap. 21).
  Se descartó skyfield porque necesita descargar efemérides de JPL en cada ejecución.
  *Validación* (tests/test_astro.py, respuestas guardadas en tests/fixtures):
  - USNO (API rstt/oneday) en Navacerrada y Fisterra, 5 fechas: orto/ocaso y crepúsculo civil a
    ≤ 3 min, salida/puesta de la luna a ≤ 4 min, iluminación a ≤ 2 puntos.
  - astropy: altura y azimut del centro galáctico a < 0,5°.
  - *Problema*: la iluminación salía ~5 puntos distinta de USNO. Con astroplan se vio que nuestra
    fórmula coincide (±0,2) y que USNO da la iluminación a las 12 h UT, no a las 0 h: era el test.
  - *Problema*: astral `dusk(observer, date, depression, tzinfo)` → pasar la zona como tercer
    argumento posicional rompía. Ahora con argumentos por nombre.
  - Nombres de fase por iluminación, como USNO (> 50 % = gibosa); USNO solo dice "cuarto" el día
    exacto y nosotros a ±3 puntos del 50 %: el test admite esa equivalencia.
- **Contaminación lumínica** (`contaminacion.py`): *World Atlas of Artificial Night Sky Brightness
  2025* de D. Lorenz (VIIRS), gratis y sin clave, en teselas PNG de 1024 px a z6 (~1/120°). Paleta de
  15 colores exactos → zona (0…7b) → brillo en el cénit (mag/arcsec²) → **Bortle aproximado**. El
  autor advierte que su mapa no es Bortle, así que la web lo muestra como "≈ Bortle". Se toma la zona
  más frecuente en 3×3 píxeles. Contraste: Puerta del Sol 7b (≈ Bortle 9), Peñalara 4b (20,7 mag,
  coincide con medidas SQM publicadas de ~20,8), Somosierra 3b.
- **Notas** (`puntuacion.py`): **aditivas**: base + factores con nombre y puntos, recortadas a 0-10.
  Así el desglose de la web es exactamente la suma ("qué suma y qué resta").
  - Luz (amanecer/atardecer): base 4; lienzo de nubes altas/medias 35-70 % +4; cielo limpio −1;
    cubierto arriba hasta −2; nubes bajas en el spot hasta −3; banco de bajas a 40 km hacia el sol
    hasta −3,5 (o +1 si está despejado y hay lienzo); lluvia hasta −3; visibilidad; reflejos en agua.
  - Astro: base 10; nubes hasta −9; luna según iluminación y horas de noche sin luna (con 3 h sin
    luna ya no resta); contaminación lumínica por zona (0 a −6); humedad, viento; +0,5 si el núcleo de
    la Vía Láctea es fotografiable ≥ 1 h sin luna. Aviso de rocío si T − Td < 2 °C.
  - Niebla: humedad, margen al punto de rocío, viento flojo y visibilidad del modelo; lluvia resta;
    "mar de nubes" (+5) si el spot está a ≥ 1000 m, despejado, y hay ≥ 60 % de nubes bajas en los
    puntos de horizonte.
  - Casos extremos en tests/test_puntuacion.py (21 tests).
- **Previsión**: 5 días, con fiabilidad alta (hoy, mañana), media (3.er día) y baja (4.º-5.º).
- **Horizonte**: puntos a 40 km hacia el orto/ocaso redondeados a 0,05° para compartir peticiones
  entre spots cercanos (menos carga para Open-Meteo).
- **Formato** de `informe.json`: por spot y día: sol, noche (luna, ventanas sin luna, Vía Láctea),
  meteo resumida y las 4 notas con desglose. Ids de spot estables y legibles (`slug-hash`).
- Se quita la salida `mapa.html` (folium) de `descubrir_spots.py`: la web la sustituye.
  `mis_spots.csv` admite líneas de comentario y el ejemplo queda comentado.
- `notificar.py` adaptado al informe nuevo, sigue desacoplado; en el workflow solo envía si existen
  los secretos de Telegram.
- Workflows: `datos.yml` cada 3 h (+ al cambiar el código de notas) y `descubrir.yml` mensual (+ al
  cambiar el código de descubrimiento), ambos en el mismo grupo de concurrencia para no pisarse al
  publicar, con reintentos de `git pull --rebase && git push`.
