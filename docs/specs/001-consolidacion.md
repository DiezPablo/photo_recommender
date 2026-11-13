# 001 — Consolidación: todo en photo_recommender

Estado: lista
Modo: ambos (Fauna sobre todo) · plataforma
Situación del fotógrafo: —

## Problema
La fauna de España está partida en dos repos: Rasante tiene observatorios (OSM + facetas de GBIF) y 32 especies
curadas; safari_recommender tiene un "modo España" mucho más rico (cuadrícula de 10 km con estacionalidad y
confianza, eBird, rarezas, hides, fenómenos, "este finde"). Rasante, a su vez, arrastra safaris del mundo, que la
visión deja fuera (decisión 0013). Resultado: duplicación, dos webs y presupuesto de Vercel gastado en lo que
no es el producto. Esta spec es el **plan**; no implementa nada.

## Alcance
- Inventario de qué se trae del modo España de safari_recommender y dónde encaja (§1-2).
- Inventario de qué se quita de safaris aquí y qué redirecciones quedan (§3).
- Riesgos (§4) y partición en specs 005-011 con criterios de aceptación (§5, y en el backlog).
- Candidatos a poda por "información justa" o terreno de PhotoPills (§6). **No se elimina nada aquí.**
- **Fuera de alcance**: implementar; tocar safari_recommender (solo lectura, queda congelado); la parte
  mundial de safaris (`/parque`, `/mapa`, `CartaMundo`, `mundo.py`…), que se queda allí.

## Criterios de aceptación
- [ ] Cada pieza del modo España tiene destino: traer (a qué módulo), fusionar con qué de Rasante, o descartar.
- [ ] Cada pieza de safaris en Rasante tiene acción (borrar / redirigir) y no queda ninguna referencia huérfana
      listada sin dueño.
- [ ] Riesgos de Vercel, workflows y secretos con mitigación concreta.
- [ ] Specs 005-011 en el backlog, cada una con criterios verificables y tamaño de una sesión.

## 1. Qué hay en safari_recommender (modo España)

| Pieza | Qué hace | Tamaño |
|---|---|---|
| `safari/espana/rejilla.py`, `zonas.py` | Cuadrícula EEA 10 km (EPSG:3035) | 90 l. |
| `gbif_descarga.py`, `estacionalidad.py`, `evaluacion.py`, `experimentos.py`, `diagnostico.py`, `cli.py` | Descarga SQL de GBIF (necesita cuenta), frecuencia por celda y mes con confianza, backtest/AUC → `espana.json` | ~740 l. |
| `ebird.py`, `ebird_frecuencia.py` | Recientes/rarezas por provincia (API eBird, clave) y frecuencia de detección → `espana_recientes.json`, `espana_rarezas.json`, `espana_ebird.json` | ~460 l. |
| `inat_espana.py` | Recientes de mamíferos/reptiles/anfibios (iNat), actividad por hora → `espana_actividad.json` | 196 l. |
| `lugares.py`, `nombres_lugares.py`, `natura.py` | Lugares: hotspots eBird + espacios protegidos (Wikidata) + observatorios OSM; límites Natura 2000 → `espana_lugares.json`, `espana_natura.json` | ~550 l. |
| `nombres.py` + `recursos/nombres_espana.csv`, `especies_estado_espana.csv` | Nombres comunes corregidos, domésticas fuera | 87 l. |
| (en `lugares`/cli) | `espana_rutas.json` (rutas OSM) y `espana_rasante.json` (enlaces a Rasante) | — |
| `src/features/carta/{CartaEspana,FichaCelda,FranjaDia,estado,geometria}` | Carta IGN con fauna por cuadrícula, fiabilidad, luz, ficha de celda; estado en la URL | ~1000 l. |
| `src/features/espana/*` | Planificador/"este finde" (`finde.ts`, `puntuacion.ts`), hides (`hides.ts`, 718 l. curadas), fenómenos, fotografía por especie, normas, rarezas, mis especies, diario, luz y mar | ~3900 l. |
| Páginas `/espana`, `/espana/{lugar/[id],especie/[clave],hides,rarezas,normas,mis-especies,diario,mapa}` y rutas JSON `/espana/{datos/[bloque],cerca,lugares,lugares-mapa,especie-datos/[clave],especies.json}` | | |
| Workflows `espana.yml` (trimestral, 5 h, GBIF), `espana_recientes.yml` (diario, eBird), `espana_actividad.yml` (semanal) | | |
| Tests `tests/test_espana_*.py` (9 ficheros) | | |

Dependencias de fuera de `espana/`: `safari.comun` (idéntico en origen a `rasante.comun`), `safari.frecuencia`
(45 l.), `safari.practico.overpass`, `@/lib/{fechas,almacen,sol,luz,luna,mareas,tiempo,rejilla}`, `@/ui/*` y,
puntualmente, `@/features/safaris/{modelo, componentes/FrecuenciaAvistamientos}`.

## 2. Qué se trae y cómo encaja (sin duplicar)

Principio: **un solo pipeline de fauna (`rasante/fauna`) y un solo área web (`src/features/fauna`)**, con
URLs bajo `/fauna`. El lugar de fauna usa el núcleo común de la spec 003; no se fusiona con los spots (0015).

**Pipeline → `rasante/fauna/`**
- Se trae: `rejilla`, `zonas`, `gbif_descarga`, `estacionalidad`, `evaluacion` (+ `frecuencia`) como
  `rasante/fauna/cuadricula/`; `ebird`, `ebird_frecuencia`, `inat_espana` como `rasante/fauna/recientes/`;
  `natura`, `nombres` y sus CSV a `rasante/fauna/` y `rasante/recursos/`.
- Se fusiona: **lugares**. Hoy hay dos: `fauna.json` (observatorios OSM agrupados + facetas GBIF) y
  `espana_lugares.json` (hotspots eBird + espacios protegidos + observatorios OSM). Queda uno: `lugares_fauna`
  = observatorios (de `rasante/fauna/osm.py`, que ya lee el PBF: se descarta la vía Overpass de `lugares.py`) +
  hotspots eBird + espacios protegidos, deduplicados por distancia, con `ccaa_de` y descarte de vecinos (0007).
  Las facetas GBIF por lugar de `rasante/fauna/gbif.py` se sustituyen por las celdas de la cuadrícula que lo
  cubren (misma información, mejor estimada).
- Se fusiona: **especies**. `especies.json` (32 curadas, consejos, foto) se mantiene como capa curada;
  la distribución y los meses salen de la cuadrícula en lugar de las facetas por provincia. `fotografia.ts`
  (dificultad y consejos) se une a `recursos/especies.csv`.
- Se fusiona: **fenómenos** (`fenomenos.ts`) con `recursos/eventos_naturaleza.csv` (categoría fauna): una sola
  lista, en el pipeline de eventos (0012).
- Se descarta: `espana_rutas.json` (ya está `rutas.json`, 0010), `espana_rasante.json` (los enlaces pasan a
  ser internos), `experimentos`, `diagnostico` (se quedan en el repo congelado como histórico).
- CLI: `python -m rasante fauna --cuadricula | --recientes | --lugares | --actividad` (mismas órdenes, un
  subpaquete).

**Web → `src/features/fauna/`**
- Se trae: `CartaEspana` + `FichaCelda` + `estado` + `geometria` como `features/fauna/carta/` (sustituye al
  mapa actual de `/fauna`); `finde.ts`, `puntuacion.ts` y el planificador como las situaciones "una tarde /
  un finde" de la visión; `hides.ts` + `CatalogoHides`; `normas.ts` (y se integra la info de dron, ver §6);
  `ListaRarezas`; `Alojamientos` solo si no duplica la logística de OSM.
- Se fusiona: ficha de lugar (`/espana/lugar/[id]` ↔ `/fauna/[id]`), ficha de especie
  (`/espana/especie/[clave]` ↔ `/fauna/especies/[id]`), calendario por grupo con `/fauna/calendario`.
- Se reutiliza de Rasante, no se trae: `lib/sol.ts`, `lib/almacen.ts`, `lib/ubicacion.ts`, `ui/mapa/useMapaBase`,
  `sw.js` (añadiendo rutas de fauna a la lista de guardables). `FranjaDia` y `LuzYMar` se comparan con la
  línea temporal de la ficha de spot y se queda una.
- Se descarta: `MisEspecies` y `Diario` (decisión 0016), dependencias a
  `features/safaris`.
- URLs: `/espana/*` no existe en Rasante, así que no hay que redirigir dentro; las rutas nuevas son
  `/fauna`, `/fauna/lugar/[id]`, `/fauna/especies/[id]`, `/fauna/hides`, `/fauna/rarezas`, `/fauna/normas`.
  `/fauna/[id]` actual redirige a `/fauna/lugar/[id]` si cambia el id.

**Workflows**: `espana.yml` → `fauna_cuadricula.yml` (trimestral, a mano también); `espana_recientes.yml` +
`espana_actividad.yml` → un `fauna_recientes.yml` diario (actividad, un paso semanal por condición). La parte
de fauna que hoy corre en `rutas.yml` (`fauna`, `especies`) pasa a `fauna_*.yml`.

## 3. Qué se quita de safaris en Rasante

| Qué | Acción |
|---|---|
| `rasante/safaris/` (8 ficheros), `rasante/recursos/safaris.csv`, orden `safaris` en `rasante/__main__.py` | Borrar |
| `src/features/safaris/`, `src/app/safaris/**` (5 páginas) | Borrar |
| `.github/workflows/safaris.yml`, `safaris_mundo.yml`; paso `--recientes` de `datos.yml` (l. 94-100) | Borrar |
| `tests/test_safaris.py`, `test_safaris_mundo.py`, sus fixtures; casos en `e2e/web.spec.ts` | Borrar |
| `next.config.ts` (`/safaris/[id]` en `outputFileTracingIncludes`), `scripts/descargar-datos.mjs` (4 ficheros, `PUBLICOS`), `src/lib/datos.ts`, `src/ui/BarraInferior.tsx`, `src/app/layout.tsx`, `src/estilos/11-calendario.css`, `src/lib/ubicacion.ts` | Quitar referencias |
| Docs: `rasante/CLAUDE.md`, `src/CLAUDE.md`, `docs/operacion.md`, `docs/hoja-de-ruta.md`, `CLAUDE.md` raíz | Quitar referencias |
| Release `datos`: `safaris.json`, `safaris_mundo.json`, `safaris_indice.json`, `safaris_recientes.json` | Borrar los assets **después** de desplegar sin ellos (si no, el prebuild de un despliegue anterior falla) |
| Caché de Actions de safaris | Dejar caducar |

Redirecciones (en `next.config.ts` `redirects()`, permanentes 308): `/safaris` y `/safaris/:ruta*` → la web
de safari_recommender (dominio por confirmar; ver Riesgos). Si no hay dominio estable, `/safaris/:ruta*` →
`/fauna` con temporal 307.

## 4. Riesgos

- **Vercel (0002)**. Quitar safaris libera `safaris_mundo.json.gz` de las funciones y `safaris_indice.json` de
  `public/datos`. El modo España añade ~6 rutas ISR, cada una con 2-6 `.gz` (`espana.json` es el grande:
  celdas × especies × 12 meses). Mitigación: medir el tamaño real de cada `.gz` antes de 006; dividir
  `espana.json` por bloques de 100 km como ya hace `/espana/datos/[bloque]` y que cada función lleve solo lo
  que lee; criterio: despliegue ≤ tamaño actual (~270 MB) medido en el build. Nada de prerenderizar fichas de
  lugar o especie salvo las 32 curadas.
- **Nº de despliegues**. Hoy: datos ×2/día + clima + safaris_mundo diario + rutas. Tras migrar: se va
  safaris_mundo (diario) y llega fauna_recientes (diario): mismo número. Agrupar la publicación de recientes
  con el `datos.yml` de la tarde si es posible (un solo commit de `version.json`).
- **Workflows**. Concurrencia: todos los que publican van al mismo grupo que `datos.yml`. `fauna_cuadricula`
  tarda hasta 5 h y depende de la cola de descargas de GBIF: incremental con caché, `--minutos`, y no publica
  si no hay descarga. Consumo de iNaturalist (≤ 1 pet/s) y Overpass compartido con `rutas.yml`: escalonar crons.
- **Secretos**. `GBIF_USUARIO`, `GBIF_CLAVE` (descarga SQL) y `EBIRD_CLAVE` (API eBird) hay que darlos de alta
  en este repo (en safari_recommender están en un *environment* de GitHub llamado `EBIRD_CLAVE`); actualizar
  `.env.example`. Sin ellos el pipeline no pide nada y la web sigue (comportamiento ya existente: mantenerlo).
  **Licencia eBird**: la API es de uso no comercial; se usa igualmente (decisión 0017, monetización aparcada).
- **Ética**: recientes de iNat/eBird sin ubicaciones exactas de lince, oso, lobo, desmán, visón, tortugas (0011);
  test que lo comprueba al migrar.
- **Datos curados con caducidad**: `hides.ts` y `fenomenos.ts` tienen revisión anual en safari_recommender
  (`revision.yml`); hay que traer esa revisión o se pudren.
- **Orden**: retirar safaris (005) antes de migrar libera presupuesto y simplifica `datos.ts`; la migración de
  datos (006-008) antes que las páginas (009-011).

## 5. Partición (añadida al backlog)

- **005 — Retirada de safaris**: todo lo de §3. CA: `grep -ri safari src rasante tests e2e .github scripts` solo
  devuelve las redirecciones; `make check` y e2e en verde; `/safaris/x` responde 30x; el build no descarga
  ficheros de safaris; assets borrados de la release tras el primer despliegue verde.
- **006 — Cuadrícula de fauna en `rasante/fauna`**: rejilla, descarga GBIF, estacionalidad con confianza y
  backtest; `fauna_cuadricula.yml`; secretos GBIF. CA: tests portados en verde sin red; sin credenciales no
  falla; `fauna_cuadricula.json` (por bloques) en la release; tamaño de cada bloque anotado en la spec.
- **007 — Lugares de fauna unificados**: observatorios OSM + hotspots eBird + espacios protegidos + Natura 2000,
  con el esquema de lugar de 003. CA: un solo fichero de lugares de fauna; ningún par de lugares a < 300 m con
  el mismo tipo; todos con `ccaa_de` y ninguno en país vecino; `fauna.json` antiguo retirado sin romper
  `/fauna/[id]` (redirección si cambia el id).
- **008 — Recientes, rarezas y actividad**: eBird + iNat; `fauna_recientes.yml`; secreto `EBIRD_CLAVE`. CA: test
  de especies sensibles sin coordenadas finas; sin clave, la web oculta el bloque; licencia de cada fuente en
  `docs/decisiones/`; un despliegue al día como mucho por este workflow.
- **009 — Carta de fauna en `/fauna`**: CartaEspana + FichaCelda sobre `useMapaBase`, estado en la URL. CA: carga
  < 300 KB de JSON en el navegador; funciona sin JS con lista de lugares; capturas móvil y escritorio.
- **010 — Fichas de lugar y especie fusionadas**: `/fauna/lugar/[id]` y `/fauna/especies/[id]` con cuadrícula,
  recientes, hides cerca, fenómenos y spots/rutas cerca (enlaces internos). CA: ISR; las 32 curadas se
  prerenderizan; e2e de una ficha de cada tipo; tamaño de función medido.
- **011 — Situaciones "una tarde / este finde" + hides, rarezas y normas**: `finde.ts`/`puntuacion.ts` con
  desglose aditivo (0003); `/fauna/hides`, `/fauna/rarezas`, `/fauna/normas` (con dron dentro); revisión anual
  de datos curados. CA: nota con desglose visible; formulario GET sin JS; incidencia automática si un hide
  tiene > 1 año sin revisar.

## 6. Candidatos a eliminar (propuesta, no se elimina nada)

- **Alineaciones de sol y luna con picos** (`rasante/eventos/alineaciones`, `alineaciones.json`): terreno de PhotoPills/TPE (alineación al minuto).
- **Panorama con trayectorias de sol, luna y Vía Láctea en la ficha**: planificación de encuadre (PhotoPills); basta "horizonte abierto al O/E" y la hora real.
- **«Sal a las…» con minutos de marcha sin luz**: planificador de toma; la ruta basta con distancia y desnivel.
- **Mareas y oleaje** (Open-Meteo Marine, ~300 llamadas/ejecución): no entra en la nota y PhotoPills lo da mejor; información de más.
- **`LuzYMar` / dirección de la luz por la mañana y la tarde** (safari_recommender): brújula de PhotoPills; no traer.
- **Rutas de senderismo como sección propia** (`/rutas`, 8500 fichas, filtros, GPX, perfil): no es "dónde fotografiar"; dejar solo "llegar andando" desde spot y lugar.
- **Logística de OSM** (aparcamiento, agua, refugio, camping, autocaravanas): información justa → como mucho el aparcamiento.
- **Dron sí/no como bloque propio**: mover a una línea en normas; cinco niveles con explicación por zona es más de lo necesario.
- **Marcador de aciertos con METAR en «Método»**: útil para validar, no para el fotógrafo; dejarlo como informe interno.
- **Avisos por Telegram** (`rasante/avisos`): opcional y sin uso; los `.ics` ya cubren avisos.
- **Calendarios `.ics` por comunidad** (18 + España): con uno nacional y el del viaje basta.
- **«Mis especies» y «Diario de salidas»** (safari_recommender): estado de usuario, no "dónde ir"; no traer.
- **Experimentos y diagnóstico de la cuadrícula** (`experimentos.py`, `diagnostico.py`): investigación ya hecha; se quedan en el repo congelado.
- **Alojamientos de fauna** (`Alojamientos.tsx`): duplica logística y no es "dónde ir"; no traer.

## Datos
Fuentes nuevas: GBIF descarga SQL (CC BY / CC0 por conjunto; EOD de eBird CC BY 4.0), API eBird (no comercial),
iNaturalist (CC BY-NC por observación, solo se publican recuentos y fotos con licencia abierta), Natura 2000
de la AEMA (reutilización libre con atribución), Wikidata (CC0), OSM (ODbL). Impacto en Vercel: §4.

## Notas de implementación
Ficheros previsibles: los de §2-3. Fuente de solo lectura: `DiezPablo/safari_recommender` (clonar en `/tmp`),
que queda congelado; su `comun` es copia del de Rasante, así que se usa el de aquí.
