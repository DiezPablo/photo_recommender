# Spots de paisaje

Bot de Telegram con Mini App de mapa para fotografía de paisaje: descubre spots a partir de lo que fotografían otros, puntúa cada día las condiciones de luz y te avisa cuando merece la pena salir. Todo con servicios gratuitos de uso personal.

```
GitHub Actions ──(cada 6 h)── condiciones.py ──► docs/datos/informe.json ─┐
      │  (mensual) descubrir_spots.py ──► docs/datos/spots.geojson ───────┤
      └─(tarde) notificar.py ──► aviso por Telegram                       │
                                                                          ▼
GitHub Pages: docs/ = Mini App (mapa) + datos ◄── la lee ── Servidor del bot (FastAPI)
                                                                ▲
                                     Telegram ──(webhook)───────┘
```

| Pieza | Qué hace |
|---|---|
| `descubrir_spots.py` | Wikimedia Commons + OpenStreetMap → spots agrupados, con nombre y momento típico (sin clave de API) |
| `condiciones.py` | Open-Meteo + astral → nota 0–10 por spot: amanecer, atardecer, astro, niebla |
| `notificar.py` | Aviso diario por Telegram con los mejores spots |
| `docs/index.html` | Mini App: mapa con notas, filtros por día y momento, ranking, ficha, cómo llegar |
| `app/` | Bot: `/hoy`, `/manana`, `/pasado`, `/spot nombre`, `/mapa`, ubicación → spots cercanos, guardar spot propio |
| `.github/workflows/` | `datos.yml` (cada 6 h + aviso de la tarde) y `descubrir.yml` (mensual) |

No hay base de datos: los datos viven en el propio repo, los publica GitHub Pages y el bot los lee de ahí. Los spots que guardas desde el bot se añaden a `mis_spots.csv` mediante la API de GitHub.

## Puesta en marcha

### 1. Datos en local
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-bot.txt
python descubrir_spots.py       # → salida/spots.geojson y salida/mapa.html
mkdir -p docs/datos && cp salida/spots.geojson docs/datos/
python condiciones.py --salida docs/datos/informe.json
python -m http.server -d docs   # Mini App en http://localhost:8000
```
Otra zona: `python descubrir_spots.py --zona "Costa da Morte" --bbox=-9.35,42.85,-8.9,43.35` (con coordenadas negativas, `--bbox=` pegado).

### 2. Bot de Telegram
0. `cp .env.example .env`, rellénalo y cárgalo con `set -a; source .env; set +a`.
1. **@BotFather** → `/newbot` → copia el token a `TELEGRAM_TOKEN`.
2. `python -m app.polling` y escribe `/start` a tu bot: te dirá tu id. Ponlo en `ALLOWED_USER_IDS` (y en `TELEGRAM_CHAT_ID`) y reinicia.
3. Prueba `/hoy`, `/spot …` o mándale una ubicación.

### 3. Publicar
1. **Repo en GitHub** con `salida/` y `docs/datos/` incluidos.
2. **Mini App**: *Settings → Pages → Deploy from a branch → main /docs*. Su URL es `WEBAPP_URL`.
   GitHub Pages en repos privados requiere plan de pago: haz el repo público (no contiene secretos) o usa Cloudflare Pages con carpeta de salida `docs`.
3. **Secretos de Actions**: `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID`. Lanza *Actions → Datos y alertas → Run workflow*.
4. **Servidor del bot**: despliega el `Dockerfile` en el mismo hosting gratuito que Gota a Gota con las variables de `.env.example`. Al arrancar registra el webhook en `PUBLIC_URL/telegram/webhook`, los comandos y el botón **Mapa**.
   Si el hosting duerme el servicio, la primera respuesta tardará unos segundos.
5. **Opcional, guardar spots desde el bot**: token *fine-grained* de GitHub con permisos de lectura y escritura en *Contents* y *Actions* solo para este repo → `GITHUB_TOKEN` y `GITHUB_REPO`.

## De dónde salen los spots
- **Wikimedia Commons**: fotos geolocalizadas de la zona. Se quedan las de calidad reconocida por la comunidad (*Quality*, *Valued*, *Featured*) o con categorías de paisaje, y se descartan interiores, retratos, mapas, fauna y flora. Un spot necesita varias fotos de al menos dos autores distintos. Las fotos de ejemplo se muestran con autor y licencia.
- **OpenStreetMap**: da nombre a los spots y añade los miradores sin fotos como spots de segunda fila (`--sin-miradores` para quitarlos).
- **Tus spots**: `mis_spots.csv`, o mándale una ubicación al bot y pulsa *Guardar*.

(Flickr sería mejor fuente por volumen, pero su API solo da claves a cuentas Pro.)

## Cómo se puntúa
- **Amanecer / atardecer**: ideal un 30–70 % de nubes altas o medias con pocas bajas. Se mira también la nubosidad baja a ~40 km en la dirección del sol: si hay un banco de nubes, el sol no las ilumina desde abajo y el cielo no se enciende. Lluvia y mala visibilidad restan.
- **Astro**: nubosidad media en la noche astronómica, penalizada por la luna según su iluminación y el tiempo sobre el horizonte.
- **Niebla**: humedad muy alta, temperatura casi igual al punto de rocío y viento flojo antes del amanecer.
- **Reflejos**: en lagos, embalses y playas se avisa si el viento es casi nulo.

Son heurísticas de partida: ajusta los pesos de `nota_luz` y compañía según lo que veas en el campo.
