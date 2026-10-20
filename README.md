# Spots de paisaje

Web personal (uso no comercial) para decidir **si merece la pena salir a fotografiar** en la Sierra de
Madrid: para cada spot y día da una nota de 0 a 10 para amanecer, atardecer, noche estrellada / Vía
Láctea y niebla, con el desglose de qué suma y qué resta. Todo con datos gratuitos y sin claves.

**Web:** https://photo-recommender.vercel.app

```
GitHub Actions ─ cada 3 h ─ condiciones.py ──► public/datos/informe.json ─┐  commit
      │          mensual ── descubrir_spots.py ► public/datos/spots.geojson ┤  al repo
      └─ (opcional) notificar.py ► aviso por Telegram                     │
                                                                          ▼
                                   Vercel: Next.js genera la web estática con esos JSON
```

| Pieza | Qué hace |
|---|---|
| `descubrir_spots.py` | Wikimedia Commons (fotos geolocalizadas de paisaje) + OpenStreetMap (nombres y miradores) → spots, con fotos de ejemplo (autor y licencia), meses más fotografiados y contaminación lumínica |
| `condiciones.py` | Open-Meteo + astronomía → `informe.json`: por spot y día, sol, luna, Vía Láctea, meteo y las 4 notas con desglose |
| `astro.py` | Sol (astral), luna (astral + iluminación de Meeus) y núcleo de la Vía Láctea (cálculo propio) |
| `contaminacion.py` | Atlas mundial del brillo artificial del cielo 2025 (D. Lorenz) → zona, mag/arcsec² y Bortle aproximado |
| `puntuacion.py` | Las fórmulas de las notas (aditivas y explicables) |
| `notificar.py` | Extra opcional: aviso diario por Telegram, desacoplado de la web |
| `src/` | Web Next.js: ranking + mapa + ficha de spot, filtros por día, tipo y distancia, temas claro/oscuro/noche (rojo) |
| `.github/workflows/` | `datos.yml` (cada 3 h), `descubrir.yml` (mensual), `pruebas.yml` (pytest + build + Playwright) |

## Cómo se puntúa
Resumen (detalle en la propia web, página *Cómo se puntúa*, y en `puntuacion.py`):
- **Amanecer / atardecer**: base 4; un lienzo de nubes altas o medias del 35-70 % suma +4; restan las
  nubes bajas en el spot y, sobre todo, un banco de nubes bajas a 40 km **en la dirección del sol**
  (impide que el sol ilumine el cielo desde abajo); restan lluvia y mala visibilidad; reflejos en agua
  con viento casi nulo.
- **Noche / Vía Láctea**: base 10; restan nubes, luna (solo si no deja ≥ 3 h de noche sin luna),
  contaminación lumínica del spot, humedad y viento; suma si el núcleo de la Vía Láctea está alto sin luna.
  Avisa de riesgo de rocío en la lente.
- **Niebla**: humedad, margen al punto de rocío y viento flojo de madrugada. En miradores y cumbres,
  estar dentro de la niebla resta (no se ve nada); lo bueno allí es el **mar de nubes**: spot alto y
  despejado con nubes bajas por debajo.
- 5 días de previsión, con aviso de fiabilidad decreciente (las nubes a más de 3 días son poco fiables).

## En local
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q                                   # tests del pipeline (sin red)

python descubrir_spots.py --salida public/datos       # tarda: Commons limita las peticiones
python condiciones.py                                 # → public/datos/informe.json

npm ci
npm run build && npm start                            # web en http://localhost:3000
npx playwright test                                   # e2e en móvil y escritorio (capturas en capturas/)
BASE_URL=https://photo-recommender.vercel.app npx playwright test   # contra producción
```
Otra zona: `python descubrir_spots.py --zona "Costa da Morte" --bbox=-9.35,42.85,-8.9,43.35` (con
coordenadas negativas, `--bbox=` pegado). Spots propios: añádelos a `mis_spots.csv`.

## Publicación
- **Vercel** sirve la web (Next.js, configuración en `vercel.json`). Cada commit a `main`, incluidos los
  de datos que hace GitHub Actions, redespliega la web.
- **GitHub Actions** recalcula los datos (no hace falta ningún secreto). Para lanzar a mano:
  *Actions → Datos → Run workflow* o *Descubrir spots → Run workflow* (con otra zona o bbox si quieres).
- **Aviso por Telegram (opcional)**: crea el bot con @BotFather, saca tu chat con
  `python notificar.py --chat-id` y añade los secretos `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID` en
  *Settings → Secrets and variables → Actions*. Sin ellos, el paso se salta.

## Fuentes y licencias
Previsión de [Open-Meteo](https://open-meteo.com/) (CC BY 4.0) · mapa y nombres © colaboradores de
[OpenStreetMap](https://www.openstreetmap.org/copyright) (ODbL) · fotos de
[Wikimedia Commons](https://commons.wikimedia.org/), siempre con autor y licencia · contaminación
lumínica del [World Atlas of Artificial Night Sky Brightness 2025](https://djlorenz.github.io/astronomy/lp/)
de D. Lorenz. Flickr se descartó porque su API solo da claves a cuentas Pro. Sin IA ni LLM.
