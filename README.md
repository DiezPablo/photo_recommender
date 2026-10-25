# Rasante

**¿Merece la pena salir a fotografiar?** Previsión para fotografía de paisaje y nocturna en toda España: cada
día, para unos 1500 spots, una nota de 0 a 10 de amanecer, atardecer, noche y Vía Láctea, niebla o mar de
nubes y salida o puesta de la luna, con el desglose de qué suma y qué resta. Además, unas 8400 rutas de
senderismo con distancia, desnivel, tiempo estimado, perfil y GPX, un calendario de qué fotografiar en cada
época (floraciones, otoño, berrea, aves, nieve, lunas, meteoros, Vía Láctea, eclipses, auroras), la climatología de
cada zona, alineaciones de sol y luna con el relieve y un planificador de viajes día a día.

**Web:** https://photo-recommender.vercel.app · Proyecto personal, sin fines comerciales. Solo datos
abiertos y gratuitos, sin claves de API, y sin IA ni LLM.

```
                ┌─────────────── GitHub Actions ────────────────┐
  Open-Meteo ──►│ python -m rasante prevision   2 veces al día  │──► informe.json ┐
  Commons, OSM,─►│ python -m rasante spots       mensual         │──► spots.geojson├─► release «datos»
  Wikidata      │                                               │                 │   + commit de
  OSM (PBF),   ─►│ python -m rasante rutas       mensual         │──► rutas.json   ┘   version.json
  FEDME, MAPA   └───────────────────────────────────────────────┘                          │
                                                                                          ▼
                             Vercel: Next.js descarga los datos al construir y publica la web
```

## Qué hay en el repositorio

| Ruta | Qué es |
|---|---|
| [`rasante/`](rasante/) | Pipeline de datos en Python (paquete): previsión y notas, descubrimiento de spots, rutas, validación, avisos |
| [`src/`](src/) | Web Next.js 16: `app/` (rutas), `features/{spots,rutas}`, `ui/`, `lib/`, `estilos/` |
| [`tests/`](tests/) | Tests del pipeline (pytest, sin red: respuestas reales grabadas en `tests/fixtures`) |
| [`e2e/`](e2e/) | Pruebas de la web en móvil y escritorio (Playwright) |
| [`.github/workflows/`](.github/workflows/) | Datos, descubrimiento, rutas, validación y pruebas |
| [`docs/`](docs/) | Arquitectura, modelos de puntuación, operación, desarrollo y registro de decisiones |
| `mis_spots.csv` | Tus spots propios (opcional): se evalúan junto a los descubiertos |

## Empezar

Requisitos: Python 3.12+ y Node 20+.

```bash
make instalar        # entorno de Python (.venv) con el paquete y las herramientas, y dependencias de la web
make check           # lint, formato, tipos y tests de Python y de la web
make web             # descarga los datos publicados, construye la web y la sirve en http://localhost:3000
```

Sin `make`: `pip install -e ".[dev]"`, `npm ci`, `npm run build && npm start`. Todas las órdenes, en
[`docs/desarrollo.md`](docs/desarrollo.md).

### El pipeline

```bash
python -m rasante --help
python -m rasante prevision --mis-spots mis_spots.csv      # → public/datos/informe.json
python -m rasante spots --total 300 --por-provincia 4      # descubrimiento (horas: mejor en Actions)
python -m rasante rutas --pbf spain-latest.osm.pbf         # extracto de OSM de Geofabrik
python -m rasante eventos                                  # → public/datos/eventos.json
python -m rasante validar                                  # validación histórica de las notas
python -m rasante avisos --prueba                          # resumen de Telegram sin enviarlo
```

## Documentación

- [Arquitectura](docs/arquitectura.md): flujo de datos, paquetes, estrategia de renderizado y límites de los servicios gratuitos.
- [Modelos de puntuación](docs/modelos.md): cómo se calcula cada nota y cómo se ha validado.
- [Operación](docs/operacion.md): workflows, calendario, lanzamientos manuales, secretos y qué hacer si algo falla.
- [Desarrollo](docs/desarrollo.md): entorno, órdenes, convenciones y pruebas.
- [Hoja de ruta](docs/hoja-de-ruta.md): hacia un planificador de viajes de fotografía y senderismo.
- [Registro de decisiones](docs/decisiones.md) y [encargo original](docs/encargo.md).

## Fuentes y licencias

Previsión de [Open-Meteo](https://open-meteo.com/) (CC BY 4.0), con CAMS (Copernicus) para aerosoles ·
mapas, nombres y rutas © colaboradores de [OpenStreetMap](https://www.openstreetmap.org/copyright) (ODbL) ·
[senderos homologados FEDME](https://misendafedme.es) (CC BY 4.0) y Caminos Naturales © Ministerio de
Agricultura, Pesca y Alimentación, vía IGN · fotos de [Wikimedia Commons](https://commons.wikimedia.org/), con
autor y licencia de cada una · lugares de [Wikidata](https://www.wikidata.org/) (CC0) · contaminación lumínica
del [World Atlas of Artificial Night Sky Brightness 2025](https://djlorenz.github.io/astronomy/lp/) (D. Lorenz) ·
relieve con las teselas Terrarium (Mapzen, AWS Open Data) · países vecinos de Natural Earth (dominio público).
