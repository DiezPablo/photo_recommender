# 003 — Esquema único de "lugar" (versión inicial)

Estado: lista
Modo: plataforma (Luz y Fauna)
Situación del fotógrafo: —

## Problema
El catálogo es el activo (visión), pero hoy hay tres formas de "sitio": spots (`spots.geojson`), lugares de
fauna (`fauna.json`) y, por llegar, los de safari_recommender (`espana_lugares.json`). Sin un esquema común no
hay resultados ni ficha compartidos entre modos (`docs/producto/modos.md`), ni se puede auditar cobertura y
licencias (002).

## Alcance
- Contrato de `lugares.json` y su validador; se genera a partir de lo que ya existe, sin tocar la web.
- **Fuera de alcance**: cambiar páginas, traer lugares de safari_recommender (007), calcular idoneidad (013),
  cambiar ids existentes, retirar `spots.geojson` o `fauna.json` (siguen siendo la fuente hasta 007 y 010).

### Esquema v1 (un objeto por lugar)
| Campo | Tipo | Notas |
|---|---|---|
| `id` | texto | `slug-hash` estable. Los ids actuales de spots y de `/fauna/[id]` se conservan |
| `nombre`, `lat`, `lon` | | Coordenadas con 5 decimales |
| `provincia`, `ccaa` | | Código INE y `ccaa_de` (0007); nunca en país vecino |
| `modos` | lista | `luz`, `fauna` o ambos |
| `tipo` | enumerado | mirador, cumbre, costa, faro, cascada, agua (lago/embalse/río), bosque, cañón, urbano, humedal, observatorio, espacio_protegido, otro |
| `fuentes` | lista | `{fuente, ref, licencia, comercial}`: Wikidata, OSM, Commons, eBird, propio… Mínimo una |
| `foto` | objeto o nulo | `{url, autor, licencia}` |
| `acceso` | objeto | `{aparcamiento_m, accesible}`; nulos si no se sabe |
| `luz` | objeto o ausente | `{cielo_mag, bortle, horizonte: apertura por 8 rumbos (grados), costa, popularidad}`. `idoneidad` por momento llega con 013 |
| `fauna` | objeto o ausente | `{observatorios, celdas: [EEA 10 km], espacio: {nombre, figura}, hides: [ids]}`. Las especies no van aquí: salen de la cuadrícula (006) |
| `eventos` | lista de ids | Eventos de `eventos.json` que ocurren en el lugar (014) |
| `revisado` | fecha o nulo | Solo en datos escritos a mano |

Reglas: un spot y un lugar de fauna a < 300 m y con el mismo nombre normalizado son **un** lugar con dos modos.
Ningún campo de un lugar sitúa una especie sensible (0011). `lugares.json` es un índice: lo pesado (previsión,
especies, galería) sigue en sus ficheros.

## Criterios de aceptación
- [ ] `rasante/recursos/lugar.schema.json` (JSON Schema) describe la tabla anterior.
- [ ] `python -m rasante lugares` genera `lugares.json` desde `spots.geojson` y `fauna.json`, lo valida contra el
      esquema y falla si algún lugar no tiene fuente con licencia, provincia o `modos`.
- [ ] Test sin red: los ids de entrada aparecen iguales en la salida; un par spot/observatorio a < 300 m con el
      mismo nombre sale como un lugar con `modos: ["luz","fauna"]`; sin NaN.
- [ ] La orden imprime un resumen (lugares por modo, tipo y comunidad; fusionados) que sirve a 002.
- [ ] `lugares.json` comprimido ≤ 500 KB; se publica en la release pero ninguna ruta web lo lee todavía (el
      diff no toca `src/`).
- [ ] Ficha `docs/decisiones/0015-esquema-lugar.md`.

## Datos
Sin fuentes nuevas. Licencias por fuente: Wikidata CC0, OSM ODbL, Commons por fichero, GBIF por conjunto.
`comercial` se rellena con lo que diga 002; hasta entonces, nulo permitido solo en ese campo. Vercel: 0 MB (no se
incluye en ninguna función todavía); +1 fichero en la release.

## Diseño
No hay interfaz.

## Notas de implementación
Nuevo `rasante/lugares/` (lectura de los dos ficheros, fusión, validación, CLI) y entrada en `__main__.py`; paso
en `datos.yml` tras spots. Riesgo: los nombres de observatorios generados ("Observatorio junto a X") no deben
fusionarse por nombre con un spot llamado X: exigir además mismo tipo de sitio o < 100 m.
