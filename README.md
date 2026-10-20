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
| `puntuacion.py` | Los modelos de las notas, explicables (desglose que suma la nota) |
| `validar.py` | Validación histórica: ERA5, fotos de Commons y METAR de aeropuertos |
| `notificar.py` | Extra opcional: aviso diario por Telegram, desacoplado de la web |
| `src/` | Web Next.js: ranking + mapa + ficha de spot, filtros por día, tipo y distancia, temas claro/oscuro/noche (rojo) |
| `.github/workflows/` | `datos.yml` (cada 3 h), `descubrir.yml` (mensual), `pruebas.yml` (pytest + build + Playwright) |

## Cómo se puntúa (modelo v2, validado)
Detalle en la web (*Cómo se puntúa*) y en `puntuacion.py`:
- **Amanecer / atardecer — camino de la luz**: lienzo de nubes altas/medias sobre el spot y hacia el
  sol; nubes bajas a 15/40/80/150 km en la dirección del sol (un banco a 30-50 km apaga el cielo);
  aire (aerosoles y calima de CAMS, humedad, aire lavado tras la lluvia); evaluado en el pico de color
  (±15 min). Confianza con un segundo modelo (ECMWF).
- **Noche**: mejor ventana de 3 h (nubes y luna hora a hora), transparencia (vapor de agua, AOD),
  contaminación lumínica del spot y cúpula de luz hacia el núcleo de la Vía Láctea o el sur.
- **Niebla**: probabilidad calibrada con 10 años de METAR de los aeropuertos de Madrid (humedad
  máxima y viento mínimo de madrugada); **mar de nubes** con el perfil vertical (techo de la capa
  baja, inversión) frente a la altura del spot.
- **Validación** (`validar.py`, workflow *Validar notas*): niebla AUC 0,92 sobre 11 792 madrugadas;
  amanecer/atardecer AUC 0,60 frente a 0,56 del modelo anterior con días fotografiados en Commons.

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
