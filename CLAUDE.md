# Spots de paisaje — contexto para Claude Code

> **Dirección actual: lee `ENCARGO.md`.** Se abandona el bot de Telegram con Mini App en favor de una web en Vercel; lo que aquí se dice del bot (`app/`, Mini App, webhook) queda obsoleto y debe eliminarse. Anota decisiones y problemas en `registro.md`.

App personal (uso no comercial) para un fotógrafo aficionado en Madrid: bot de Telegram con Mini
App de mapa que descubre spots de fotografía de paisaje, puntúa a diario las condiciones de luz y
avisa. Todo con servicios gratuitos. **Sin IA/LLM por decisión del usuario.** Ver README para la arquitectura.

## Piezas
- `descubrir_spots.py`: Wikimedia Commons (geosearch + categorías de calidad/paisaje, sin clave) → DBSCAN
  haversine → nombres OSM (Overpass) → momento típico (astral); miradores OSM sin fotos como spots `origen=osm`.
  Flickr descartado: su API solo da claves a cuentas Pro.
- `condiciones.py`: Open-Meteo + astral → `docs/datos/informe.json` (nota 0-10 por spot y momento).
- `notificar.py`: aviso HTML por Telegram; el bot reutiliza `construir_mensaje`.
- `app/`: FastAPI con webhook (`app/main.py`), lógica en `app/bot.py`, modo local `python -m app.polling`.
  Sin estado ni base de datos: lee los JSON publicados en `DATOS_URL` (por defecto `WEBAPP_URL/datos`)
  y guarda spots propios en `mis_spots.csv` vía API de GitHub (`app/github.py`).
- `docs/index.html`: Mini App estática (Leaflet + Telegram WebApp SDK), servida por GitHub Pages.
- Workflows: `datos.yml` (cada 6 h, aviso a las 17:17 UTC) y `descubrir.yml` (mensual).

## Estado
- Todo probado solo con datos simulados (Telegram y GitHub simulados, Mini App en Chromium headless).
  **Nunca se ha ejecutado contra Commons, Overpass, Open-Meteo ni Telegram reales.**
  Lo primero a validar con datos reales: las listas PALABRAS_PAISAJE / PALABRAS_EXCLUIR y el tamaño de tesela.

## Próximos pasos
1. Ejecutar `descubrir_spots.py` real (Sierra de Madrid); revisar spots con el usuario y ajustar
   `--radio`, `--min-fotos`, `--min-autores` y la puntuación.
2. `condiciones.py` real y validar notas contra algún atardecer real.
3. Bot real con `python -m app.polling`; luego desplegar el Dockerfile y GitHub Pages.

## Convenciones
- Python 3.12, código, comentarios y mensajes en español.
- Secretos solo por variables de entorno (`.env`, ver `.env.example`); nunca en código ni commits.
- JSON publicados sin NaN (`allow_nan=False`): el navegador no los acepta.
- Bbox con coordenadas negativas: `--bbox=-4.30,40.60,-3.55,41.10` (con `=`).
- Respetar límites de las APIs: caché en `cache/`, pausas y `maxlag` en Commons, User-Agent descriptivo (política de Wikimedia).
