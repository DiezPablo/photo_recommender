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

## 2026-10-20 · Primera ejecución real y ajustes

### Descubrimiento real (GitHub Actions, Sierra de Madrid, bbox -4.30,40.60,-3.55,41.10)
- 88 teselas, **6189 fotos geolocalizadas**, 1104 pasaban el filtro de paisaje; 20 clusters; 700
  elementos OSM, 155 miradores sin fotos (72 sin nombre). ~15 min en Actions, sin ningún 429.
  overpass-api.de dio HTTPError y respondió el espejo francés: los espejos funcionan.
- **Problemas vistos al revisar los spots uno a uno** y cómo se resolvieron:
  - Fotos de la **ISS** ("Earth viewed from space") geolocalizadas en la sierra, un Gran Premio de camiones,
    trenes AVANT, cigüeñas ("Ciconia ciconia" no contiene "birds"), culebras (un cluster de culebras se
    llamaba "Cabeza de Hierro Mayor"), iglesias, la Plaza Mayor de Segovia, fiestas de pueblo, un instituto
    → nuevas palabras de exclusión.
  - "río" casaba con "Navas de Riofrío" (pueblo) → las palabras se comparan **al inicio de palabra**
    (regex), lo que sigue admitiendo plurales.
  - Nombres con ids de Flickr, fechas y numeración ("EMBALSE DE SANTILLANA (6495112213)",
    "Puente de Navalacarreta (2 de mayo de 2015, …) 09") → `limpiar_nombre`.
  - Mejor fuente de nombre: **la categoría específica de Commons más repetida en el cluster**
    ("Laguna de los Claveles", "Embalse de Santillana"), traducida si está en inglés con patrones
    ("X Reservoir" → "Embalse de X"). Orden: OSM con nombre a ≤ 400 m → categoría → OSM a ≤ 600 m →
    título limpio. Nombres repetidos se numeran.
  - Miradores OSM sin nombre: toman el del elemento con nombre más cercano ("Mirador junto a Laguna
    Grande de Peñalara") o se descartan si no hay ninguno a 2,5 km.
  - Agrupación: con radio 250 m y 4 fotos salían 19-20 spots; con **300 m y 3 fotos (de ≥ 2 autores)**,
    28 spots, todos de paisaje real (Mirador del Último Pino con el Alcázar, Buitrago, Laguna de los
    Claveles, Bola del Mundo, Bosque de Finlandia, embalses, cascadas…).
- Para ajustar sin volver a pedir nada a Commons, `descubrir_spots.py` vuelca las respuestas crudas
  (`salida/volcado/`, artefacto del workflow) y admite `--desde-volcado DIR`.

### Notas revisadas con los datos de hoy (20-oct)
- **Niebla saturaba**: madrugada con humedad 100 % y visibilidad 0,4 km en casi toda la sierra → nota
  10 de niebla en 175 de 175 spots, y el ranking "Todo" era solo niebla. Pero en un mirador o una
  cumbre, estar dentro de la niebla es no ver nada. *Cambio*: dos escenarios y se queda el mejor:
  niebla en el spot (buena en bosques, ríos, embalses; −5,5 × probabilidad en miradores y cumbres) y
  **mar de nubes** (spot ≥ 900 m fuera de la niebla con nubes bajas debajo). Tras el cambio: 6 spots
  con niebla ≥ 6,5 hoy.
- Atardecer de hoy: 75 % de nubes altas/medias y horizonte oeste despejado → 7-8 en casi toda la
  zona. Coherente con la previsión cruda; el tiempo es regional, así que muchos spots puntúan parecido
  y lo que los distingue es el horizonte hacia el sol, la contaminación lumínica y el tipo.
- No se puede contrastar con el cielo real desde aquí: queda para el usuario apuntar en el campo si
  la nota acierta y ajustar los pesos de `puntuacion.py`.

### Web
- Next.js 16 con páginas estáticas (206 páginas con los datos reales), filtros como enlaces (funciona
  sin JS) y Leaflet con import dinámico. Primer despliegue en Vercel sin tocar el panel: bastó
  `vercel.json` con `"framework": "nextjs"`.
- *Problema*: el build fallaba porque componentes de cliente importaban de un módulo que usa `node:fs`
  → separado en `src/lib/modelo.ts` (puro) y `src/lib/datos.ts` (servidor).
- *Problema*: en el contenedor, Chromium no cargaba teselas. Playwright envía también localhost por el
  proxy (405) → el servidor de pruebas escucha en la IP de la máquina y esa IP se excluye del proxy.
  Además, la geolocalización solo funciona en contexto seguro: en local el test deja la ubicación
  guardada; en producción (https) usa el botón real.
- Ajustes tras revisar capturas: cabecera en móvil (el enlace "Cómo se puntúa" se partía), controles
  de zoom blancos en modo noche, bandera de colores en la atribución de Leaflet.
- Workflow `datos` falló la primera vez porque arrancó antes de que existieran spots y `git add` de un
  fichero inexistente rompía → se comprueba antes. Acciones de GitHub actualizadas a sus versiones
  actuales (avisaban de Node 20 obsoleto).

### Segunda zona: Costa da Morte (workflow con `publicar=false`, solo artefacto)
- 1467 fotos geolocalizadas, pero solo 279 pasaban por paisaje: faltaban términos gallegos y de costa
  ("Cabo Finisterre", "Fervenza do Ézaro", "Monte Pindo", "praia", "punta", "miradoiro"…).
  Añadidos (también catalán/asturiano básicos: "platja", "cala"…) → 433 fotos y **25 spots, todos de
  costa de verdad** (Cabo Fisterra, Fervenza do Ézaro, Punta do Roncudo, Praia de Niñóns, Cabo Touriñán…).
  Traducción "Beach of X" → "Playa de X". Las fotos de la ISS también aparecían allí (ya excluidas).
- El pipeline de condiciones funcionó igual (84 spots, notas coherentes: atardeceres de 9+ en las
  puntas el 21-oct con lienzo de nubes y horizonte oeste despejado sobre el mar).
- Nota: un `workflow_dispatch` en el grupo de concurrencia reemplaza al run pendiente del mismo grupo
  (GitHub solo guarda uno en espera); por eso un descubrimiento de Madrid salió "cancelled" y se relanzó.
- *Problema* (workflows): un run de descubrimiento encolado hizo checkout de su commit (anterior) y, al
  publicar, `git pull --rebase` chocó con el `spots.geojson` que otro run acababa de publicar →
  conflicto y fallo. *Solución*: checkout de `main` al empezar y `.github/scripts/publicar.sh`, que
  parte siempre del último `origin/main`, copia encima los ficheros generados (mandan ellos, no hay
  nada que fusionar) y reintenta el push. Probado en local con un remoto simulado y dos publicadores.
- Revisando la galería en producción: una foto de *calidad* del salón del trono del Alcázar pasaba
  como paisaje porque bastaba con ser "Quality image". Ahora hace falta siempre una palabra de paisaje;
  la calidad solo ordena. Mismo número de spots, galerías sin interiores.
- Commons sirve miniaturas de tamaños estándar: pedíamos 640 px y llegaban de 960 px para tarjetas
  de 150-320 px → se piden de 500 px.
- Desde el contenedor algunas miniaturas dan 429 (IP compartida); los navegadores de verdad no.
- *Problema* (visto como test intermitente contra producción): si se pulsa un botón de tema antes de
  que React hidrate la página —fácil con mala cobertura en el campo— no pasaba nada. *Solución*: el
  cambio de tema lo hace un manejador de clic delegado en el script en línea del `<head>`, activo desde
  el primer pintado; React solo refleja el botón activo. Test nuevo que bloquea el JS de la app y
  comprueba que el modo noche se activa igual. Otros reintentos contra producción eran de red (proxy):
  repetidos sin reintentos, 6/6 en verde.

## Estado final (20-oct-2026)

### Definición de hecho
- [x] **Pipeline real con datos reales y tests en verde**: descubrimiento real en Actions (Sierra de
  Madrid: 27 spots con fotos + ~145 miradores OSM con nombre) y probado en Costa da Morte (23 spots);
  condiciones con Open-Meteo real; 68 tests de pytest (astronomía contra USNO/astropy, notas con
  casos extremos, pipeline con respuestas reales guardadas, JSON sin NaN).
- [x] **Web con todo lo de "Qué debe mostrar"**, probada en móvil y escritorio (16 tests e2e de
  Playwright en local y contra producción, capturas revisadas en claro, oscuro y noche, sin errores de consola).
- [x] **Notas explicables**, validadas con casos sintéticos y revisadas con los datos del 20-oct (de ahí
  el cambio del modelo de niebla). Falta el contraste en el campo, que solo puede hacer el usuario.
- [x] **GitHub Actions actualiza solo**: `datos` (cada 3 h), `descubrir` (mensual) y `pruebas`; varias
  ejecuciones correctas lanzadas por push y a mano (workflow_dispatch). La primera programada con el cron nuevo
  es a las 09:23 UTC del 20-oct.
- [x] **Vercel**: `npm run build` limpio, `vercel.json` incluido y desplegando en
  https://photo-recommender.vercel.app con cada commit (también los de datos).
- [x] `README.md`, `CLAUDE.md` y este registro al día.
- [x] Sin secretos en el código (búsqueda de patrones de tokens sin resultados; Telegram solo por secretos de Actions).

### Pendiente / ideas
- Ajustar los pesos de `puntuacion.py` con la experiencia en el campo (apuntar nota prevista vs. resultado).
- Notificaciones push de verdad (fuera de alcance por decisión del encargo).
- Más zonas a la vez: hoy la web publica una zona (Madrid); `descubrir.yml` admite otra zona y bbox,
  pero publicarla sustituye a la anterior. Para varias, habría que fusionar geojson por zona.
- El mapa general con ~170 marcadores se ve denso en móvil; si crece, agrupar marcadores (clustering).
