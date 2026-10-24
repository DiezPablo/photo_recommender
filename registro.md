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

## 2026-10-20 · Modelo de predicción v2

### Investigación (qué hace bueno un amanecer, una noche o una niebla)
- **Sunsethue** (whitepaper): trazado de rayos desde el observador hasta la base de las nubes y de
  ahí hacia el sol; si algo bloquea el rayo del sol, la nube no se enciende. Las nubes medias y altas
  reflejan mejor; la humedad en superficie resta. https://sunsethue.com/whitepaper
- **NOAA/SPC, "The Science of Sunsets"** (Corfidi): el ingrediente común de los colores vivos es el
  **aire limpio**; los aerosoles bajos y la calima los apagan; cirros y altocúmulos son los que se
  encienden; una capa media/alta continua con una franja despejada en el horizonte "baña de rojo".
  https://www.spc.noaa.gov/publications/corfidi/sunset
- **Stephen Bay** (fotógrafo): un banco de nubes a 30-50 km mar adentro bastó para que no hubiera
  color; el pico es ~15-20 min antes del amanecer; contrastar modelos (ICON/ECMWF mejor que GFS).
  https://stephenbayphotography.com/blog/predicting-sunrise-and-sunset-colors/
- **Sunsethue blog / dZoom**: cobertura ideal 30-75 % (40-60 %), nubes altas siguen encendidas hasta
  ~30 min tras la puesta, mejor tras una tormenta (aire limpio), menos humedad = colores más vivos.
- **Noche** (PictureCorrect, Astrospheric, The Photographer's Ephemeris): para Vía Láctea importa la
  **transparencia** (vapor de agua, humo, polvo, cirros finos), no el seeing; mirar las nubes en la
  dirección de la foto; la luna solo molesta si está arriba; el rocío.
- **Niebla de radiación** (NWS): cielo despejado de noche (el suelo se enfría), margen al rocío
  pequeño, viento flojo pero no nulo, lluvia la tarde anterior la hace mucho más probable; los
  cirros la frenan. **Mar de nubes** (AEMET, divulgameteo): el techo de la niebla es el tope de la
  inversión térmica, normalmente de unos cientos de metros.

### Qué cambia (puntuacion.py v2, condiciones.py)
- **Amanecer/atardecer**: pico de color (±15 min) con interpolación horaria; lienzo = 60 % sobre
  el spot + 40 % a 15-40 km hacia el sol; **camino de la luz** con nubes bajas a 15/40/80/150 km
  (transmisión multiplicativa, una capa media espesa lejana corta la luz a las altas); nubes bajas
  locales tapan el lienzo; **aire**: AOD y polvo de CAMS, humedad, aire lavado tras lluvia; lluvia.
- **Noche**: calidad hora a hora (nubes y luna) y **mejor ventana de 3 h**; transparencia (vapor de
  agua total, AOD, humedad); contaminación local recalibrada (un Bortle 4 despejado sí merece la
  pena: ≥ 8); **cúpula de luz** hacia el núcleo de la Vía Láctea o el sur (atlas a 10-75 km);
  rachas graduadas.
- **Niebla**: probabilidad de niebla de radiación con margen al rocío, viento, nubosidad de la noche
  previa y lluvia de 36 h; **mar de nubes** con el perfil por niveles de presión (1000-700 hPa) en los
  puntos del llano a 40 km: techo de la capa, cobertura e inversión encima, frente a la altura del
  spot. Se descartan los niveles por debajo del suelo (extrapolados por el modelo).
- **Confianza** por nota: se recalcula con las nubes de ECMWF IFS; si difieren > 3 puntos, baja.
- Peticiones: ~13 variables en el spot, 3 en los puntos del camino (rejilla gruesa lejos), 32 en
  los perfiles, 4 del segundo modelo y AOD/polvo por celda de 0,4°: unas 400 "llamadas" por
  ejecución, dentro del límite gratuito de Open-Meteo.
- **Validación histórica** (`validar.py`, workflow `validar.yml`): días con foto de puesta/salida en
  Commons (Madrid y Segovia) frente al resto del mismo mes, con ERA5 2016-2025; AUC de v1 frente a v2.

### Validación empírica y ajustes (validar.py, 20-oct)
- **Amanecer/atardecer**: 91 días positivos (fotos de Commons en la ventana de color: búsquedas
  "sunset/atardecer Madrid/Segovia…" + fotos de paisaje de la Sierra) frente a 7306 eventos de
  2016-2025 con ERA5. AUC mismo mes: v1 0,557 → v2 0,599 (amanecer 0,59 → 0,66). Sin el camino de
  la luz, v2 cae a 0,573: es lo que más aporta. Diagnóstico: los días fotografiados tienen menos
  nubes bajas (6 % frente a 11-20 %), menos nubes bajas en el camino y más nubes altas (40 % frente
  a 29-32 %), pero **menos medias** → peso de las medias en el lienzo 0,85 → 0,5 (las variantes 0,3-0,7
  difieren ~0,01 de AUC, dentro del ruido; no se ajusta más).
  *Problemas*: las categorías de Commons que supuse no existían (0 ficheros) → búsqueda de texto;
  "sunset Toledo" devolvía Toledo (Ohio); metadatos vacíos llegan como lista.
- **Calima**: el 15-mar-2022 (150+ µg/m³) ERA5 lo veía como 100 % de nubes altas y v2 daba 5,3 →
  el polvo resta más (×0,35 a 150 µg/m³) y vela también la luz directa: ahora 2,5-3.
- **Niebla**: 11 792 madrugadas de METAR (Barajas, Getafe, Cuatro Vientos, Torrejón) vía Iowa
  Environmental Mesonet. Primera v2 (margen al rocío + noche despejada + lluvia previa) era **peor**
  que la fórmula antigua (AUC 0,864 frente a 0,912). Ajuste con años 2016-2021 y prueba en 2022-2025:
  humedad máxima 85→100 % × viento mínimo 6→20 km/h = 0,913 en prueba (techo de una regresión
  logística: 0,923). La nubosidad nocturna y la lluvia previa no aportaban → fuera. Probabilidad
  **calibrada** con la frecuencia observada (índice máximo ≈ 46 % de madrugadas con niebla).
  Resultado final: AUC 0,920; cuando dice 30-50 %, hubo niebla el 42 % de las veces.
- **No validado empíricamente** (sin verdad disponible gratis): la nota nocturna (las nubes y la luna
  son deterministas una vez prevista la nubosidad; la contaminación lumínica viene del atlas) y el mar
  de nubes (no hay observaciones del techo de la niebla). Quedan razonados físicamente y con tests.

## 2026-10-23 · Recomendador de toda España

### Decisiones (el usuario pidió España entera, predicciones de todo y que la orientación la decida yo)
- **Spots** (`descubrir_espana.py`): candidatos de Wikidata (lugares con foto P18 y artículos:
  ~2700 montañas, ~1300 playas, lagos, embalses, cascadas, miradores, cabos, faros, cañones,
  acantilados) y de OpenStreetMap por bloques de 2° (miradores con nombre, cumbres con Wikidata,
  cascadas, faros, cabos, acantilados). Se fusionan (mismo Wikidata o < 400 m), se asigna provincia
  y comunidad (polígonos del IGN simplificados en `datos_base/provincias.geojson`) y se puntúa la
  popularidad con las fotos de Commons a menos de 500 m. Selección: los 12 mejores de cada provincia
  + el resto por nota nacional hasta ~1500. El primer cálculo hace ~13 000 peticiones a Commons:
  caché persistente en Actions y corte por tiempo (`--minutos`), la siguiente ejecución continúa.
- **Orientación = horizonte del terreno** (`horizonte.py`): teselas Terrarium de AWS (gratis, sin
  clave), ángulo del relieve cada 2° hasta 60 km con curvatura y refracción, zoom 12/11/10 según la
  distancia. Contraste: Peñalara 2415 m (real 2428) abierto en todas direcciones; Puerto de
  Navacerrada tapado al este por la Bola del Mundo (6,7°); Embalse de Santillana con La Pedriza al
  norte; Fisterra abierto al oeste sobre el mar. Se usa para la hora real a la que el sol asoma o se
  esconde tras el relieve (astral `time_at_elevation`), restar la luz rasante y el cielo bajo cuando
  una montaña tapa el sol, que la luna tras una montaña no ilumine, que el núcleo de la Vía Láctea
  tenga que asomar 2° sobre las crestas, y el panorama de la ficha.
- **Nuevo tipo: luna** (salida o puesta sobre el paisaje en el crepúsculo, ± 75 min del atardecer o
  amanecer): iluminación, altura del sol (ideal entre -6° y +2°, paisaje y luna equilibrados), relieve
  y nubes hacia la luna. El 26-oct-2026 la luna llena sale a las 18:12 con el sol a +1°: nota 10.
- **Fotos de Google**: no es posible gratis (la API de Places es de pago, pide clave y sus
  condiciones prohíben guardar las fotos). Cada ficha enlaza "Ver fotos en Google Maps".
- **Límites de Open-Meteo** (gratis: 10 000 llamadas/día, 600/min, por IP; >10 variables cuenta
  más): en el spot se piden exactamente 10 variables (nubosidad total y punto de rocío se derivan),
  rejillas compartidas (spot 0,05°, camino del sol 0,1-0,5°, perfil vertical 0,5°, segundo modelo
  0,25°, aerosoles 0,4°), ritmo ≤ 450 llamadas/min y **2 actualizaciones al día** (≈05:47 y 14:47).
- **Publicación**: con ~1500 spots el informe pesa ~20 MB y no puede ir al historial de git en cada
  actualización. Va a la release `datos` (se sobrescribe) y un commit mínimo
  (`public/datos/version.json`) hace que Vercel reconstruya; `scripts/descargar-datos.mjs` descarga
  los datos antes de cada build (si no puede, usa los locales).
- **Web**: ranking con el top 60 nacional en el HTML (sin JavaScript) y la lista completa en JSON
  estático por día y tipo (`/datos-ranking/[d]/[tipo]`) para filtrar por distancia y comunidad;
  mapa con todos los spots como puntos en canvas (miles sin ralentizar el móvil); ficha con panorama
  del horizonte (sol, luna, Vía Láctea), horas reales sobre el relieve y provincia.
- **Fallo corregido**: dos actualizaciones del 21-oct cayeron porque Open-Meteo respondió 200 con el
  cuerpo vacío; ahora se reintenta.

## 2026-10-23 · Rediseño de la web
- Tipografías Fraunces (títulos) e Inter (interfaz) con `next/font` (autoalojadas en el build).
- Notas como anillos (SVG, `Anillo.tsx`); los colores de nota pasan a la variable `--color-nota`.
- Portada: «Mejor plan» destacado (foto de Commons o cielo dibujado según la salida) y matriz
  «Los próximos días» (mejor nota por tipo y día, enlaza a cada ranking). Ranking con miniatura.
- Ficha: portada con foto, anillos de hoy, «El plan de hoy» (línea temporal 4:00→7:00 del día
  siguiente con hora azul/dorada, Vía Láctea y cada salida con su nota).
- Mapa: se probó CARTO (Voyager/Dark Matter), pero ahora devuelve una tesela «API key required";
  se mantiene OSM estándar invertido con CSS en los temas oscuros.

## 2026-10-23 · Segunda vuelta de diseño: «Rasante»
- La primera vuelta (anillos, tarjetas con degradado, píldoras, Fraunces + Inter sobre beige) tenía todos
  los tópicos de una web hecha con IA. Nueva dirección: almanaque de campo.
- Marca «Rasante» (la luz rasante del amanecer y el atardecer), con un sol sobre el horizonte como logo.
- Archivo (con eje de anchura: cifras estrechas) + IBM Plex Mono para rótulos y datos. Filetes en lugar
  de tarjetas, sin sombras ni esquinas redondeadas.
- Una sola escala de color, la de la luz: gris → ocre → naranja → bermellón.
- Portada: titular, mejor spot con cifra grande y foto (con crédito), almanaque tipo × día que hace de
  filtro (sustituye a las píldoras), ranking numerado y mapa a sangre (gris, que destaquen los puntos).
- Ficha: título grande, ficha técnica, foto con crédito, lectura de hoy (cifra + medidor), «el día, hora a
  hora» y desglose como libro de cuentas.
- Modo rojo: ningún bloque grande brillante (las casillas excelentes van con borde).

## 2026-10-23 · Descubrimiento nacional: segundo intento
- OSM ya va en una consulta por bloque (≈15 min en total) y Commons respeta su presupuesto de 150 min
  (5500 de 14 519 candidatos contados; el resto se puntúa con Wikidata y se completa en las siguientes
  ejecuciones gracias a la caché).
- Cayó en la última fase (galerías, ~1450/1500) por `int(NaN or 0)`: en Python NaN es «verdadero».
  Corregido con `_entero()` y prueba. La caché se guardó, así que el reintento reutiliza Commons y el DEM.

## 2026-10-24 · Primer descubrimiento nacional publicado (1500 spots) y correcciones
- Terminó bien (run 40021211378): 1500 spots en las 52 provincias, todos con horizonte y contaminación
  lumínica, 1193 con fotos. Pero al revisarlos por comunidad:
  - **Comunidades cruzadas**: `datos_base/provincias.geojson` traía un código de comunidad con otra numeración
    y se le puso el nombre según el INE (Asturias → «Ceuta», A Coruña → «Comunitat Valenciana»). Ahora la
    comunidad sale del código INE de provincia (`comun.CCAA_POR_PROVINCIA`, `ccaa_de`), también en
    `condiciones.py`, así que el informe se corrige sin esperar al descubrimiento.
  - **Spots en Portugal** (Marvão, São Mamede, Poço do Inferno) por los polígonos simplificados en la raya:
    se descartan los puntos dentro de un país vecino (Natural Earth 10m, `datos_base/vecinos.geojson`,
    con 200 m de margen; los del mar se mantienen, que son cabos y faros).
  - **Sesgo urbano**: contar fotos de Commons a 500 m premia los centros de ciudad («Mural», «calle de los
    cuchilleros», Madrid centro). Se resta según el cielo del atlas (−1,6 bajo 18,5 mag/″², −0,9 bajo 19,5,
    −0,3 bajo 20,5, +0,3 desde 21,3): los iconos urbanos con cientos de fotos siguen entrando.
  - **Nombres genéricos** de OSM fuera («Mural», «Picnic», «Spotting», «Begiratokia»…).
