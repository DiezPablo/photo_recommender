# 003 — Núcleo común de "lugar" (versión inicial)

Estado: lista
Modo: plataforma (Luz y Fauna)
Situación del fotógrafo: —

## Problema
El catálogo es el activo (visión). Rasante tiene dos: spots de luz y lugares de fauna. No se fusionan (decisión
0015), pero resultados, mapa, plan y auditoría (002) necesitan tratarlos igual: mismo identificador, territorio,
fuentes, foto y acceso. Hoy cada uno tiene su forma, heredada del mock (0016).

## Alcance
- Contrato de `lugares.json` (índice de los dos catálogos) y su validador.
- **Fuera de alcance**: páginas; traer lugares de safari_recommender (007); idoneidad (013). El esquema no está
  obligado a conservar ids, nombres de campo ni ficheros del mock.

### Esquema v1 (un objeto por lugar)
| Campo | Tipo | Notas |
|---|---|---|
| `id` | texto | `slug-hash`, estable desde esta versión |
| `catalogo` | `luz` \| `fauna` | Exactamente uno. Un mismo sitio físico puede estar en los dos como dos lugares |
| `nombre`, `lat`, `lon` | | Coordenadas con 5 decimales |
| `provincia`, `ccaa` | | Código INE y `ccaa_de` (0007); nunca en país vecino |
| `tipo` | enumerado | Luz: mirador, cumbre, costa, faro, cascada, agua, bosque, cañón, urbano. Fauna: humedal, observatorio, espacio_protegido, punto_de_observacion. Común: otro |
| `fuentes` | lista | `{fuente, ref, licencia}`; mínimo una |
| `foto` | objeto o nulo | `{url, autor, licencia}` |
| `acceso` | objeto | `{aparcamiento_m, accesible}`; nulos si no se sabe |
| `cerca` | lista de ids | Hasta 5 lugares del **otro** catálogo a ≤ 15 km, por distancia |
| `luz` | solo si `catalogo: luz` | `{cielo_mag, bortle, horizonte: apertura por 8 rumbos, costa, popularidad}`; `idoneidad` llega con 013 |
| `fauna` | solo si `catalogo: fauna` | `{observatorios, celdas: [EEA 10 km], espacio: {nombre, figura}, hides: [ids]}`. Las especies salen de la cuadrícula (006), no van aquí |
| `eventos` | lista de ids | Eventos que ocurren en el lugar (014) |
| `revisado` | fecha o nulo | Solo en datos escritos a mano |

Ningún campo sitúa una especie sensible (0011). Es un índice: previsión, especies y galería van en sus ficheros.

## Criterios de aceptación
- [ ] `rasante/recursos/lugar.schema.json` (JSON Schema) describe la tabla; `luz` y `fauna` son excluyentes
      según `catalogo`.
- [ ] `python -m rasante lugares` genera `lugares.json` con los spots y lugares de fauna disponibles, lo valida y
      falla si a un lugar le falta fuente con licencia, provincia o `catalogo`.
- [ ] Test sin red: salida válida contra el esquema; `cerca` solo contiene ids del otro catálogo y a ≤ 15 km;
      ids únicos; sin NaN.
- [ ] La orden imprime un resumen (lugares por catálogo, tipo y comunidad) que sirve a 002.
- [ ] El diff no toca `src/`; el tamaño comprimido de `lugares.json` queda anotado en esta spec.

## Datos
Sin fuentes nuevas. Licencias: Wikidata CC0, OSM ODbL, Commons por fichero, GBIF por conjunto. Vercel: 0 MB
(ninguna función lo lee todavía); +1 fichero en la release.

## Diseño
No hay interfaz.

## Notas de implementación
Nuevo `rasante/lugares/` (lectura, validación, `cerca`, CLI) y entrada en `__main__.py`. Entrada provisional:
`spots.geojson` y `fauna.json`; cuando 007 unifique los lugares de fauna, cambia la entrada, no el contrato.
