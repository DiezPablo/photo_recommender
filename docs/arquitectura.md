# Arquitectura

## Visión general

Rasante tiene dos piezas desacopladas que se comunican solo por ficheros JSON:

1. **Pipeline de datos** (`rasante/`, Python): corre en GitHub Actions, consulta servicios abiertos y genera
   `informe.json` (previsión y notas), `spots.geojson` (spots), `rutas.json` (rutas) y `eventos.json` (calendario).
2. **Web** (`src/`, Next.js 16, App Router): se construye en Vercel leyendo esos JSON y publica páginas
   estáticas o generadas bajo demanda.

Los datos **no van en git**: se suben como ficheros de la release `datos` del repositorio
(`.github/scripts/publicar_release.sh`, que los sobrescribe en cada publicación) y solo se hace commit de
`public/datos/version.json` con sus huellas. Ese commit dispara el despliegue de Vercel, que descarga los
datos antes de construir (`scripts/descargar-datos.mjs`, *prebuild*).

```
servicios abiertos ──► rasante (Actions) ──► release «datos» ──► Vercel (prebuild + next build) ──► web
                                        └──► commit version.json ──┘
```

## Pipeline (`rasante/`)

| Paquete | Responsabilidad |
|---|---|
| `comun` | Caché en disco (`CacheJson`), sesiones HTTP con User-Agent, JSON sin NaN, identificadores, territorio (provincia, comunidad por código INE, descarte de países vecinos) |
| `cielo` | Sol, luna y Vía Láctea (`astro`); contaminación lumínica y cúpula de luz (`contaminacion`) |
| `terreno` | Altura y horizonte a partir del modelo digital de elevaciones (`horizonte`) |
| `notas` | Modelos de nota con desglose: `luz`, `noche`, `niebla`, `luna` sobre `base` |
| `prevision` | Cliente de Open-Meteo con ritmo y caché (`openmeteo`), series horarias, carga de spots, evaluación y CLI |
| `spots` | Descubrimiento nacional: candidatos (Wikidata, OSM), Commons (popularidad, galería), nombres, selección, CLI |
| `rutas` | Rutas: OSM (PBF), FEDME y Caminos Naturales (IGN), geometría, métricas (MIDE), fusión y duplicados, CLI |
| `validacion` | Validación histórica (ERA5, Commons, METAR) frente a los modelos v1 |
| `eventos` | Calendario: fases de la luna, lluvias de meteoros con la luna de esa noche, ventanas de Vía Láctea, eclipses y eventos de naturaleza con lugar y fechas habituales (`recursos/eventos_naturaleza.csv`, revisado a mano) |
| `avisos` | Resumen diario por Telegram (opcional) |
| `recursos` | Datos de referencia: provincias (IGN), países vecinos (Natural Earth), positivos de validación |

Punto de entrada único: `python -m rasante <orden>` (`rasante/__main__.py`), que delega en el `cli.py` de
cada paquete.

### Dependencias entre paquetes

```
prevision ──► notas, cielo, terreno, comun
spots ──────► cielo, terreno, comun
rutas ──────► terreno, comun
validacion ─► notas, cielo, comun
eventos ────► cielo, comun
avisos ─────► (solo lee informe.json)
```

`notas` no depende de nada del proyecto: recibe datos ya preparados y devuelve la nota con su desglose. Eso
permite probar los modelos con casos sintéticos (`tests/test_puntuacion.py`).

## Web (`src/`)

| Ruta | Contenido |
|---|---|
| `app/` | Rutas de Next.js, finas: obtienen datos y componen funcionalidades |
| `features/spots/` | Portada (almanaque, destacado, ranking, mapa), ficha del spot, modelo de datos, lectura del informe (`datos.ts`, solo servidor) |
| `features/eventos/` | Calendario por meses, ficha de evento, barra del año, mapa de áreas y eventos cercanos a un spot o ruta |
| `features/rutas/` | Buscador, mapa, ficha, perfil, GPX, modelo y lectura de `rutas.json` (solo servidor) |
| `ui/` | Piezas compartidas: `Cifra`, iconos, selector de tema, `useMapaBase` (Leaflet) |
| `lib/` | Estado del navegador con `useSyncExternalStore` (`almacen`: localStorage, URL) y ubicación |
| `estilos/` | CSS por áreas, importado en orden desde `app/globals.css` |

Los módulos que leen ficheros con `fs` importan `server-only`: si un componente de cliente los importara, el
build fallaría en lugar de meter `fs` en el paquete del navegador.

### Estrategia de renderizado

| Página | Cómo se genera | Por qué |
|---|---|---|
| `/`, `/dia/[d]/[tipo]` | Estática (build) | Pocas combinaciones (5 días × 6 filtros) |
| `/datos-ranking/[d]/[tipo]` | JSON estático (build) | Lista completa para filtros de distancia y comunidad |
| `/spot/[id]` | Las 60 del ranking de hoy en el build; el resto bajo demanda (ISR) | 1500 fichas eran ~800 MB |
| `/rutas`, `/rutas/[ccaa]` | Estática | Buscador (cliente) y listados sin JavaScript |
| `/datos-rutas/indice`, `/datos-rutas/celda/[c]` | JSON estático | Índice compacto y trazados por celdas de 1° |
| `/ruta/[id]` | Bajo demanda (ISR) | 8400 fichas eran ~720 MB |
| `/calendario`, `/calendario/[mes]`, `/evento/[id]` | Estática | 12 meses y ~45 eventos |

Las páginas bajo demanda leen los JSON en la función del servidor (`outputFileTracingIncludes` en
`next.config.ts`) y quedan en caché hasta el siguiente despliegue, que llega con cada actualización de datos.

Sin JavaScript funcionan la portada, los filtros de día y tipo (son enlaces), las fichas y los listados de
rutas por comunidad. La distancia a tu ubicación, los mapas y el buscador de rutas necesitan JavaScript.

## Límites que condicionan el diseño

| Servicio | Límite | Cómo se respeta |
|---|---|---|
| Open-Meteo | 10 000 llamadas/día, 600/min (más caras con muchas variables) | Puntos redondeados y agrupados, ritmo por minuto, 2 ejecuciones al día |
| Wikimedia Commons | Limita por IP (429), pide `maxlag` y User-Agent | Caché persistente en Actions, `Retry-After`, pausa, presupuesto de minutos por ejecución |
| Overpass | Corta consultas grandes | Una consulta por bloque de 4°, espejos; las rutas usan el extracto PBF en lugar de Overpass |
| Vercel (Hobby) | 1 GB de ficheros estáticos, 45 min de build | Datos fuera del build (release) y fichas bajo demanda |
| GitHub Actions | 6 h por trabajo | El descubrimiento corta las consultas a Commons a tiempo y continúa la siguiente vez |
