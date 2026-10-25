# Registro de decisiones y problemas

Diario de decisiones y problemas desde el encargo original ([`encargo.md`](encargo.md)). Lo más reciente, abajo. Los nombres de ficheros de las entradas antiguas son los de entonces (antes del paquete `rasante`, oct-2026).

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

## 2026-10-24 · Segundo descubrimiento nacional (con filtros) y ajustes
- 1500 spots: ninguno fuera de España ni con nombre genérico; salen más iconos de paisaje (Cabo de Gata,
  Trafalgar, Bolonia, Calar Alto, Cap de Creus, Teide, Torrent de Pareis, Bola del Mundo). 639 con cielo
  ≥ 21 mag/″² y 81 bajo 18,5 (iconos urbanos con muchas fotos).
- Niebla: la regla «visibilidad del modelo < 1 km ⇒ ≥ 60 %» (no calibrada con METAR) exige ahora humedad
  ≥ 90 %; en Lagos de Cabdella daba niebla con un 71 % de humedad y salía como mejor plan de España.
- Mapa de portada: se encuadra la península (Canarias alejaba el encuadre hasta Francia y Marruecos).

## 2026-10-24 · Apartado de rutas de senderismo (independiente de los spots)
- Fuentes gratuitas: **OSM** (relaciones `route=hiking/foot` de un extracto PBF de España: Geofabrik u
  openstreetmap.fr; Overpass no aguanta una consulta nacional y desde el contenedor ni responde),
  **senderos FEDME** del IGN (GR 1492, PR 1648, SL 320 etapas; CC BY 4.0) y **Caminos Naturales** (MAPA, 743).
  Descartados Wikiloc/AllTrails/Komoot: sus condiciones prohíben robots y descargas masivas.
- La FEDME tiene huecos (en la Sierra de Madrid solo 3 etapas del GR 300; OSM tiene el GR 10, los PR-M y las
  rutas de Peñalara). Un sendero oficial que coincide ≥ 70 % con una ruta de OSM le pone el nombre oficial y el
  enlace; si no, entra como ruta propia (≈ 1950 coinciden, ≈ 2250 nuevas).
- Fuera: superrutas (relaciones de relaciones; sus etapas ya están), redes de bici/caballo, sin nombre ni ref,
  < 0,5 km, fuera de España.
- Sentido de marcha: orden de los miembros de la relación (suele ir de `from` a `to`); si no, desde el extremo
  más bajo. Sin esto «La Barranca – La Maliciosa» salía con +0/−813 m.
- Desnivel con el DEM a 30 m, suavizado (5 puntos) e histéresis de 3 m; tiempo por el método MIDE; esfuerzo
  estimado (no es la valoración MIDE oficial). Comprobado en la Sierra: Circular de la Pedriza 22,8 km,
  +1306 m, 8 h 30; Cuerda Larga 19,9 km, ~7 h 15.
- Web: `/rutas` (filtros en el navegador sobre un índice compacto; mapa con el inicio de cada ruta y los
  trazados por celdas de 1° al acercarse), `/rutas/[ccaa]` (listado completo, sin JS) y `/ruta/[id]` (ficha,
  mapa, perfil SVG, GPX generado en el navegador). Colores de la señalización: rojo GR, amarillo PR, verde SL.
- Primera ejecución completa (local, 40 min, la mayor parte bajando teselas del DEM): 8500 rutas, 23,6 MB.
  1555 en Cataluña, 1319 en Andalucía, 1061 en Aragón… 18 comunidades. 4490 solo de OSM, 1628 OSM con nombre
  FEDME, 1680 solo FEDME, 702 de Caminos Naturales. Comprobadas Anillo de Picos, Carros de Foc, Caminito del Rey.
- Nombres: rutas con solo número («19», «02 SE») → «Sendero 19: Es Pujols – Ses Illetes» o «SL 8 (Málaga)»;
  tramos con el mismo nombre (69 «Camino Natural del Ebro») → «…(tramo 9 de 22, Zaragoza)».
- Las 8500 fichas prerenderizadas ocupaban ~720 MB (HTML + 4 RSC por página): con los spots se pasa del
  límite de 1 GB de ficheros estáticos de Vercel. Las fichas se generan al visitarlas (ISR, `revalidate = false`)
  y `rutas.json` va en la función (`outputFileTracingIncludes`). La salida del build sigue en ~860 MB.
- Orden por defecto «Destacadas»: senderos oficiales y señalizados primero (el alfabético empezaba por «02 SE»).

## 2026-10-24 · Revisión: geometría de rutas, duplicados y tamaño del build
- El perfil salía más corto que la ruta en 718 rutas: el muestreo tomaba las rectas de más de 500 m (vías
  verdes, pistas simplificadas) por huecos entre tramos. Ahora el recorrido es una lista de trozos en orden de
  marcha (se funden los que están a < 30 m); los huecos ni se recorren ni se dibujan (el trazado y el GPX van
  por trozos: antes se unían con rectas falsas).
- Duplicados (113 casos de misma salida, llegada y distancia: etapas del GR 131 que son también Camino
  Natural, tramos repetidos del Ministerio): se queda la mejor fuente, salvo dos códigos oficiales distintos.
- Rutas de más de 12 h de marcha (Camino Mozárabe, 416 km) se muestran en jornadas de ~7 h.
- Los filtros de /rutas van en la URL: sobreviven a ir a una ruta y volver, y se pueden compartir.
- Build: las fichas de spot ocupaban 803 MB (1500 × ~530 KB de HTML + RSC), a 100 MB del límite de Vercel.
  Se prerenderizan solo las 60 del ranking de hoy; el resto, ISR como las rutas. Salida del build: 863 → 92 MB,
  tiempo 165 → 32 s.

## 2026-10-24 · Fuera el rojo: hora dorada y hora azul
- Al usuario no le gustaba el rojo. Además comunicaba alarma justo en las notas excelentes. Nueva paleta con
  sentido fotográfico: **hora dorada** para la escala de notas (gris → arena → ámbar → bronce dorado) y **hora
  azul** para la interfaz (acento, foco, selección, ubicación). Logo y favicon: sol dorado.
- Legibilidad: en tema claro las cifras de nota se mezclan un 16 % con la tinta (el ámbar puro sobre papel no
  llega al contraste de texto); en oscuro van puras y la casilla excelente lleva texto oscuro sobre dorado.
- La puesta de sol (mapa y horizonte) pasa del acento a bronce: una puesta no puede ser azul.
- Se mantienen el modo rojo nocturno (funcional) y el rojo de los GR (es la marca oficial del sendero).

## 2026-10-25 · Toque más moderno
- De «almanaque de filetes» a tarjetas: superficies blancas con esquinas de 18/12/8 px y sombra suave sobre el
  papel cálido; filetes negros fuera. La identidad se mantiene (Archivo, cifras estrechas, hora dorada y azul).
- Rótulos en sans en versalitas (la mono queda para cifras y datos: almanaque, horas, desglose).
- Cabecera translúcida con desenfoque; navegación y selector de tema en cápsulas (segmented control).
- Mapa como tarjeta flotante y fija en escritorio; botones, campos y chips redondeados con foco visible;
  acciones principales en cápsula negra; micro-transiciones (respetan `prefers-reduced-motion`).
- Almanaque con celdas redondeadas separadas; casilla actual con anillo azul; días de la ficha como acordeones.

## 2026-10-25 · «Cerca de mí» no parecía funcionar
- Sí obtenía la ubicación, pero la lista seguía siendo el ranking nacional («Cualquier distancia», «Por nota»)
  y solo aparecía en pequeño la distancia de cada spot. Ahora, al obtenerla, se filtra a 100 km (rutas: 50 km
  y por cercanía), el mapa se centra en ti y se dice en claro («23 spots a menos de 100 km de ti…»).
- Errores explicados: permiso bloqueado (con la ruta de ajustes en iPhone) o sin señal (reintento automático
  con la ubicación aproximada). Función común `pedirUbicacion()` en `src/lib/ubicacion.ts`.

## 2026-10-25 · Proyecto profesional: paquete, estructura por funcionalidades y herramientas
- **Pipeline → paquete `rasante`** (antes 11 scripts sueltos en la raíz): `comun` (caché, red, JSON, ids,
  territorio), `cielo` (astro, contaminación lumínica), `terreno` (horizonte), `notas` (un módulo por tipo de
  salida), `prevision` (Open-Meteo, series, evaluación, CLI), `spots`, `rutas`, `validacion`, `avisos`.
  Una sola entrada: `python -m rasante <orden>`. Dependencias y herramientas en `pyproject.toml`.
- Fuera el **descubrimiento antiguo de la Sierra** (`descubrir_spots.py`), sustituido por el nacional; de él
  solo seguían vivos los auxiliares de Commons (ahora `rasante.spots.commons`).
- **Caché unificada** (`rasante.comun.cache.CacheJson`) con el mismo formato de ficheros de antes, para no
  invalidar la caché de Actions (horas de peticiones a Commons).
- La primera ejecución real tras el troceo falló por un **import diferido dentro de una función**
  (`from astro import …` en `cupula`) que ni ruff ni los tests veían (los tests sustituyen esa función).
  Test nuevo que importa todos los módulos del paquete.
- **Web por funcionalidades**: `src/features/{spots,rutas}` (componentes, modelo, datos de servidor marcados
  con `server-only`), `src/ui` (piezas comunes, `useMapaBase` para los dos mapas, antes duplicado),
  `src/lib` (almacén externo, ubicación) y `src/estilos` (CSS por áreas, mismo orden de cascada).
- **Estado externo con `useSyncExternalStore`** (ubicación, preferencias, filtros en la URL, tema) en lugar
  de copiarlo con `setState` dentro de efectos (lo marca la regla `react-hooks/set-state-in-effect`).
- Al unificar los mapas apareció un **bucle de render**: el hook avisa al mover el mapa → el mapa de spots
  se renderiza → `lineas = []` crea un array nuevo → se repinta y reencuadra → el mapa se mueve… La página
  no daba error pero nunca terminaba de navegar. Lo cazaron las pruebas e2e; arreglado con una constante.
- Herramientas: ruff (lint + formato) y pytest para Python; ESLint (config de Next), Prettier y `tsc` para
  la web; todo en CI (`pruebas.yml`). `Makefile` con las órdenes habituales. Documentación en `docs/`.
- Spots propios (`mis_spots.csv`): ahora con provincia, comunidad y horizonte del terreno.

## 2026-10-25 · Filtro de desnivel en rutas

- Petición del usuario: filtrar rutas por desnivel. Rangos de desnivel positivo acumulado según la
  distribución real de las 8500 rutas (mediana ~300 m, percentil 90 ~950 m): hasta 300 m, 300-600,
  600-1000, 1000-1500 y más de 1500 m. Va en la URL (`?desnivel=`) como el resto de filtros.
- Con cinco desplegables el texto se cortaba en escritorio; «Ordenar» pasa a la cabecera de la lista
  (ordena resultados, no los filtra) y los cuatro filtros quedan en 2×2 en móvil y 4 columnas en escritorio.

## 2026-10-25 · Calendario de eventos

- Petición del usuario: qué se puede fotografiar en cada época y en cada sitio, como primer paso hacia un
  planificador de viajes (ver `hoja-de-ruta.md`).
- **Cielo, calculado**: lunas nuevas y llenas (extremos de la iluminación de `astro`; contrastadas con
  astropy: error < 1 h, fechas exactas), máximos de las lluvias de meteoros (fechas IMO) con la luna que habrá
  a la hora de observar, temporada del núcleo de la Vía Láctea (horas por noche a mitad de cada mes en el centro
  peninsular) y ventanas sin luna alrededor de cada luna nueva. Eclipses: lista fija con los del IGN/OAN
  (2 ago 2027 total en el Estrecho; 26 ene 2028 anular al atardecer); se muestran todos los futuros.
- **Naturaleza, revisada a mano**: `rasante/recursos/eventos_naturaleza.csv` (44 eventos: floraciones, otoño,
  berrea, aves, nieve, agua) con fechas *habituales* MM-DD, punto y radio. No hay fuente abierta y gratuita de
  fenología por lugar; las fechas cambian cada año y la web lo dice. Provincia y comunidad con `Provincias`
  (el Hayedo de Montejo caía en Guadalajara por el polígono simplificado: punto movido 1 km al oeste).
- Se genera en `datos.yml` (segundos) y se publica en la release como el resto. Web: `/calendario` (mes en
  curso), `/calendario/[mes]`, `/evento/[id]` (spots y rutas de la zona, noches sin luna de la temporada) y
  «A lo largo del año» en las fichas de spot y de ruta (eventos cuyo radio + 15 km incluye el punto).
- Cabecera: con «Calendario» no cabía en 375 px; por debajo de 430 px queda solo el logo.


## 2026-10-25 · «Sal a las…»: rutas y luz juntas

- Primer paso de la hoja de ruta (ver `hoja-de-ruta.md`). En la ficha de una ruta, la hora de salida para estar
  en el punto más alto 30 min antes de que salga el sol o al empezar la hora dorada (sol a 6°), para hoy y los
  dos días siguientes, con la nota prevista del spot más cercano a la cima (< 3 km) y los minutos de marcha sin
  luz (antes del alba o después del crepúsculo civil, bajando 20 min después de la puesta).
- Cima: punto más alto del perfil (si la ruta sube ≥ 100 m y se llega en ≤ 8 h); tiempo MIDE del tramo con la
  misma histéresis de 3 m que el pipeline, +15 % de margen. Vuelta por el mismo camino si no es circular.
- Sol en TypeScript (`src/lib/sol.ts`, NOAA): coincide con `rasante.cielo.astro` en ±1 min; Canarias en su hora.
- En la ficha de un spot, «Subir andando»: rutas cuya cima está a < 1 km, con las horas de hoy y mañana.
- Las funciones de spot y ruta (ISR) llevan ahora los cuatro JSON (`outputFileTracingIncludes`).

## 2026-10-25 · Avisos en el calendario (.ics), gratis y sin cuenta

- Los competidores cobran las alertas (Alpenglow Pro, Sunsethue Alerts). Aquí: un calendario iCalendar por
  zona (`/alertas/espana.ics` y uno por comunidad), estático y rehecho con cada build (dos veces al día), sin
  servidor ni cuentas. Página `/alertas` con «Suscribirse» (`webcal://`) y cómo añadirlo en Google y Outlook.
- Contenido: momentos con nota ≥ 8 (hasta 5 por día en España, 3 por comunidad, un momento por spot) en su
  franja (hora azul → fin de la dorada; noche sin luna; madrugada para la niebla), con el porqué y el enlace;
  lunas, máximos de meteoros, ventanas de Vía Láctea, eclipses y eventos de naturaleza en su mejor momento.
- UID estable por spot, día y momento: al refrescar, el calendario corrige o quita lo que cambió.
- Horas del informe en `zona_horaria` (Europe/Madrid también para Canarias: pendiente de pasar a hora local
  en el pipeline). Validado con la librería `icalendar` y en el e2e (líneas ≤ 75 octetos, CRLF).

## 2026-10-25 · Web instalable y sin conexión

- En el monte no hay cobertura y Wikiloc, Komoot o PhotoPills funcionan sin red. Ahora Rasante se instala
  (manifest con iconos generados del logo) y un service worker propio (`public/sw.js`, sin librerías):
  páginas red primero (5 s) con copia de lo visitado (60 páginas), `/_next/static` caché primero, teselas de
  OSM (1500) y fotos (150) solo de lo que el usuario ha visto (no se descargan zonas por adelantado: la
  política de teselas de OSM lo prohíbe).
- «Guardar para sin conexión» en las fichas de spot y ruta: caché aparte que no se recorta y se refresca al
  volver a visitarla. El GPX se genera en el navegador, así que también funciona sin red.
- `/sin-conexion` lista lo guardado con un script en línea: sin red, el JavaScript de esa página puede no
  estar en el dispositivo y React no hidrataría.
- `/sw.js` con `Cache-Control: no-cache` (vercel.json) para que las versiones nuevas lleguen enseguida.
- Prueba e2e real: levanta su propio servidor en localhost (el service worker exige origen seguro y
  `setOffline` no corta la red del service worker), guarda una ruta, apaga el servidor y la abre.

## 2026-10-25 · Auroras y cielos Starlight

- **Auroras**: pronóstico Kp a 3 días de NOAA SWPC (JSON público, sin clave; se admite también su formato
  antiguo). Kp máximo de las horas de noche de cada noche; aviso «norte» con Kp ≥ 7 y «casi toda España» con
  Kp ≥ 8 (como en mayo y octubre de 2024, vistas sobre todo en fotos). El aviso aparece en la portada y el
  calendario solo cuando hay algo que ver, y entra en los `.ics`; el calendario dice siempre el Kp previsto.
  Si NOAA no responde, el calendario se publica igual sin ese dato.
- **Starlight**: la Fundación Starlight publica nombres, no límites. `recursos/starlight.csv`: las 22
  Reservas y los Destinos con límites claros (islas, parques), con centro y radio aproximados (Sierra Morena
  en seis círculos) o provincia entera (Soria). La ficha del spot muestra «Cielo certificado» advirtiendo que
  la zona es aproximada. Faltan Destinos municipales pequeños.

## 2026-10-25 · Climatología: qué esperar cada mes (más allá de los 5 días de previsión)

- El hueco que no cubre nadie: las apps de previsión llegan a 3-5 días y las de planificación no saben del
  tiempo. `rasante.clima` usa ERA5 (archivo de Open-Meteo, 2021-2025) en una rejilla de 0,5° (302 puntos:
  tierra y franja costera, con Canarias y Baleares) y los **mismos modelos de nota** que la previsión:
  frecuencia por mes de amaneceres y atardeceres ≥ 7 (con el camino del sol interpolado entre puntos
  vecinos), noches con ≥ 3 h seguidas despejadas (nubosidad total < 20 %) y madrugadas con niebla (media de
  la probabilidad calibrada con METAR).
- Coste: Open-Meteo cuenta ~130 llamadas por punto (5 años, 7 variables). Para no competir con la previsión
  (~5400 llamadas por ejecución), `clima.yml` corre a las 08:17 y 20:17 UTC con 4000 llamadas como máximo y
  100 s entre puntos (< 5000/hora); guarda en caché un resumen diario compacto por punto y publica
  `clima.json` cuando la rejilla está completa (~5 días). Luego solo recalcula si cambia el código.
- Limitaciones: ERA5 es de ~30 km, así que no ve nieblas de valle pequeño ni nubes de relieve fino; la
  niebla está calibrada en el llano de Madrid. Se presenta como «lo habitual», no como previsión.
- Web: «Qué esperar cada mes» en la ficha de cada spot y de cada evento (tabla de 12 meses teñida respecto al
  mejor mes de cada fila, «1 de cada N» en el mes en curso) y «Dónde suele ir mejor» en cada mes del
  calendario (con el spot con más fotos de cada zona como referencia). Solo aparece con `clima.json`.
- Primera ejecución en Actions: un punto se cortó por tiempo de espera y paró todo. Ahora se reintentan
  también los timeouts y un punto que falla queda para la siguiente ejecución.

## 2026-10-25 · Alineaciones de sol y luna con los picos del horizonte

- La función estrella de PhotoPills o The Photographer's Ephemeris, pero automática para cada spot:
  `rasante.eventos.alineaciones` busca los picos del perfil del horizonte (cada 2°, prominencia ≥ 1°,
  altura ≤ 15°: más alto es la pared de un cañón) y los días en que el sol o la luna casi llena (≥ 85 %, con
  el sol entre −8° y +3°) salen o se ponen justo por ellos (±1° de azimut) en los próximos 12 meses.
- Sol y luna en una rejilla de 10 min común a todos los spots y numpy por spot (~30 s para 1500 spots). Luna
  de astral con paralaje (0,95° · cos h) y refracción de Sæmundsson: frente a astropy, < 0,01° en el sol y
  < 0,07° en la luna. Test con un pico sintético: los días coinciden con astropy (26-29 oct, 12-15 feb).
- Se calcula en `datos.yml` (`python -m rasante alineaciones`) y se publica `alineaciones.json`. Web: lista
  en «Horizonte y orientación» de cada spot y «Sol y luna por los picos» en cada mes del calendario.

## 2026-10-25 · Planificador de viaje (`/viaje`) y barra inferior en el móvil

- El núcleo de la hoja de ruta: zona (comunidad, toda España o «cerca de mí» con radio) y fechas (hasta 7
  días) → cada día amanecer, atardecer y noche con su spot, una ruta de un día (≤ 6 h; la que sube al spot si
  existe, con «sal a las…»), naturaleza en marcha, alineaciones, luna, meteoros, eclipses y auroras.
- Dentro de los 5 días de previsión manda la nota prevista (de noche, la Vía Láctea o la luna sobre el
  paisaje, la que tenga mejor nota); después, la climatología del mes (de noche, ponderada por la oscuridad
  del cielo) y, con la luna por encima del 60 %, noche de paisaje con luna. Se evita repetir spot salvo que
  el repetido sea claramente mejor. Las horas se calculan en hora local (Canarias incluida).
- Página dinámica (depende de los parámetros): formulario GET que funciona sin JavaScript; la función lleva
  los JSON con `outputFileTracingIncludes` y responde en ~50 ms en caliente. El plan se exporta a `.ics`.
- Con cuatro secciones la cabecera no cabía en el móvil: por debajo de 820 px las secciones van en una barra
  inferior con iconos (a mano del pulgar) y la cabecera recupera el nombre.

## 2026-10-25 · Logística de OpenStreetMap: aparcamientos, agua, refugios, campings

- `rasante.logistica`: una pasada por el extracto PBF de España (el mismo de las rutas, en `rutas.yml`) con
  filtro por claves y posiciones de nodos (áreas en su centro): aparcamientos (sin privados ni subterráneos),
  agua potable (fuentes y manantiales con `drinking_water=yes`; un manantial sin etiqueta no cuenta),
  refugios guardados y libres y abrigos de montaña, áreas de autocaravanas y campings. ~145 000 puntos en
  2,5 min y 4,4 GB de memoria.
- Los más cercanos a cada spot y a la salida de cada ruta con un índice de celdas de 0,1°, sin repetir el
  mismo sitio mapeado dos veces: aparcamiento ≤ 1,5 km, agua ≤ 2, refugio ≤ 6, autocaravanas y camping ≤ 15.
- Web: «Para ir» en las fichas, con enlace a OSM y «cómo llegar» al aparcamiento. Tests con un OSM XML.

## 2026-10-25 · «Nubes ahora»: satélite en tiempo real en los mapas

- Para decidir «¿salgo ya?» a las seis de la tarde manda lo que se ve, no el modelo. EUMETSAT publica por WMS,
  sin clave ni restricciones (`AccessConstraints: none`, `Fees: none`), el GeoColour RGB del satélite MTG
  (color real de día, infrarrojo de noche) cada 10 min. Botón «Nubes ahora» en todos los mapas; la capa se
  refresca cada 10 min mientras está activa.
- El tinte de los temas pasa de todo el panel de teselas al mapa base, para que el satélite se vea con sus
  colores; en modo noche se tiñe de rojo como las fotos.

## 2026-10-25 · Marcador de aciertos con METAR

- El color de un atardecer no se puede verificar cada día sin fotos; sus ingredientes sí. `rasante.verificacion`
  guarda en cada ejecución de `datos.yml` lo previsto para 35 aeropuertos (una sola petición multipunto a
  Open-Meteo) y lo compara al día siguiente con el METAR (Iowa Environmental Mesonet): niebla al amanecer (FG o
  visibilidad < 1 km), atardecer tapado por nubes bajas o medias (BKN/OVC/VV ≈ ≥ 70 %) y noche con ≥ 3 h
  seguidas sin BKN/OVC. Mismos criterios y ventanas horarias para lo previsto y lo observado.
- Marcador de los últimos 30 días con la previsión del día anterior, frente a la persistencia («mañana igual
  que hoy») para que el porcentaje signifique algo. Historial de 60 días en la release (`verificacion.json`).
- No se pudo rellenar hacia atrás: la API de ejecuciones anteriores de Open-Meteo guarda humedad y viento del
  día anterior, pero no las nubes. El marcador empieza el 25-10-2026 y aparece en «Método» con ≥ 100 casos.
- El METAR apenas informa de nubes altas: no verifica el «lienzo» de cirros, solo si algo lo tapa. Se dice.

## 2026-10-25 · Sin conexión: la página de aviso no rompía la hidratación… hasta que la rompía

- En la CI fallaba a ratos la prueba sin conexión. Dos causas: (1) el service worker servía la página «sin
  conexión» con la URL pedida; si React hidrataba (su JavaScript ya en caché), el enrutador de Next intentaba
  cargar esa otra ruta sin red y mostraba su error. Ahora redirige a `/sin-conexion`. (2) El script en línea
  que lista las fichas guardadas modificaba el HTML antes de que React hidratase (error #418 y luego
  `removeChild`). Ahora espera 1,5 s y solo actúa si React no ha cargado; si carga, la lista la pinta
  `ListaGuardadas`. La prueba visita antes `/sin-conexion` con red para cubrir el caso con React.

## 2026-10-25 · Canarias en su hora en toda la previsión

- El informe daba todas las horas en hora peninsular, también en Canarias (una hora más que la local). Ahora
  cada spot se evalúa en su zona (`Atlantic/Canary` si la longitud es < −12°) y el informe lo dice por spot
  (`zona_horaria`). Las series de Open-Meteo siguen pidiéndose en hora peninsular: `series` pasa cada instante
  con zona a la de las series antes de buscar, para no desfasar una hora (test con un caso de Tenerife).
- Los calendarios `.ics` convierten con la zona de cada spot.

## 2026-10-25 · Spots y rutas cruzados

- Antes solo se relacionaba una ruta con un spot si su punto más alto estaba a < 1 km. Ahora `pasoPor`
  busca el punto del trazado más cercano al spot (proyección sobre cada segmento en un plano local), los km
  desde la salida y el tiempo MIDE hasta allí (ida y vuelta por el mismo camino). «Llegar andando» en la ficha
  del spot (rutas que pasan a < 300 m, de la que llega antes a la que más tarda; fuera las de < 10 min) con la
  hora de salida para el amanecer y el atardecer; «Spots en el camino» en la ficha de la ruta, en orden y con
  la nota de hoy. El planificador usa la misma función. De 12 a 26 de los 60 spots del día con ruta a pie.

## 2026-10-25 · Planificador con mapa y viajes coherentes

- Mapa del viaje con las paradas de cada día (amanecer, salida de la ruta, atardecer, noche) numeradas por
  día y unidas en orden, y los km entre paradas en línea recta. No se calculan rutas por carretera: los
  servidores públicos gratuitos de OSRM no admiten uso sistemático; se dice «en línea recta».
- El primer plan saltaba de punta a punta de la comunidad (131 km entre paradas en un día de Asturias). Ahora
  cada elección resta un punto de nota por cada 40 km más allá de 15 desde la parada anterior (y el amanecer
  de mañana, desde donde acabó la noche): solo compensa ir lejos si la luz es claramente mejor. En el mismo
  plan de Asturias, 37-48 km al día.

## 2026-10-25 · Más eventos y CSV a prueba de comas

- Siete eventos más con lugar y fechas fiables: lavanda de Tiedra, girasoles de Tierra de Campos, descorche de
  Los Alcornocales, vendimia en La Rioja, nieblas del valle del Ebro (boira, mar de nubes desde las sierras),
  nieve en Guadarrama y otoño en la Val d'Aran. Se dejan fuera luciérnagas, orquídeas o tormentas: no tienen
  un lugar y unas fechas que se puedan sostener.
- Al añadirlos, unas comas sin comillas desplazaban campos sin que nada fallara. `naturaleza.cargar` rechaza
  ahora filas con campos de más o vacíos (test).

## 2026-10-25 · «Esta temporada» en la portada

- Las funciones nuevas no se veían desde la portada, que es donde entra todo el mundo. Bloque «Esta temporada»
  con los eventos más cerca de su mejor momento (como mucho dos por categoría, para que no salga solo otoño) y
  accesos a «Planifica un viaje» y al calendario.

## 2026-10-25 · Spots de observación de fauna

- Petición del usuario. Fuentes abiertas y sin clave: los **observatorios** de OpenStreetMap
  (`leisure=bird_hide` / `wildlife_hide`, 574 en España; fuera los privados), agrupados a < 700 m (en un
  humedal suele haber varios: 386 zonas), y **GBIF** (agrega eBird, iNaturalist, Observation.org…): por cada
  zona, facetas de especies y meses de aves y mamíferos a ~2 km en 2016-2025 (una petición; no se descargan
  registros) y el nombre común en español más repetido de cada especie. Las especies sensibles ya llegan con la
  ubicación generalizada por los conjuntos de datos.
- `python -m rasante fauna` en `rutas.yml` (mensual, usa el mismo extracto PBF); caché de GBIF de 25 días.
- Web: sección **Fauna** (buscador por lugar o especie, comunidad y «buen mes», con mapa), ficha de cada lugar
  (especies con barra relativa, observaciones por mes, rutas que pasan, eventos cerca), «Fauna cerca» en las
  fichas de spot, «Observatorios de fauna en la zona» en los eventos (más en los de fauna) y, en el
  planificador, el lugar más cercano al día con ese mes entre los buenos. Quinta sección en la navegación.
- Las observaciones por mes miden también cuándo va la gente a mirar; se dice en la ficha.
- Los observatorios sin nombre en OSM (más de la mitad) se nombran por el núcleo de población más cercano a
  < 8 km («Observatorio junto a Villafáfila»), leído en la misma pasada por el extracto.
- El mapa de eventos y fauna ajusta la vista sin animación: si se desmonta a mitad de zoom (cambio de filtro o
  de página), Leaflet fallaba con `_leaflet_pos`. GBIF limita la faceta de especies a 300: se dice «más de 300».

## 2026-10-25 · Paisaje y fauna, separados

- Petición del usuario: la berrea es fauna; las Perseidas, paisaje. Dos ámbitos con un único criterio
  (`ambito(e)`: la categoría «fauna» es fauna; el resto, paisaje y cielo) aplicado en toda la web:
  - `/calendario` es el del **paisaje y el cielo** (floraciones, otoño, nieve, agua, paisaje + luna,
    meteoros, Vía Láctea, eclipses, auroras) con un aviso enlazado «Fauna en {mes}: …».
  - `/fauna/calendario` y `/fauna/calendario/[mes]`: eventos de fauna y los observatorios en su mejor momento
    ese mes. Pestañas «Paisaje y cielo / Fauna» que mantienen el mes; en Fauna, «Lugares / Calendario».
  - Fichas: «A lo largo del año» solo paisaje; «Fauna cerca» + «Fauna a lo largo del año» aparte (spots,
    rutas y lugares de fauna). La ficha de un evento enlaza al calendario de su ámbito.
  - Portada: «Esta temporada» en dos columnas. Planificador: la naturaleza del día es el paisaje; los eventos
    de fauna van en la línea «Fauna» junto al observatorio. `.ics`: los de fauna, con «Fauna:».
