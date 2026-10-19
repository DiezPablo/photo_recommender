# Encargo: web de condiciones para fotografía de paisaje y nocturna

Este documento es el encargo completo. **Ejecútalo de principio a fin de forma autónoma**: decide,
construye, prueba, corrige y repite hasta cumplir la "Definición de hecho". No pidas confirmación
para decisiones técnicas; toma la que consideres mejor y anótala en `registro.md`.

## Objetivo
Web para un aficionado a la fotografía (Madrid, uso personal, sin fines comerciales) que muestre,
para una lista de spots de paisaje y de cielo nocturno, **si merece la pena salir** y por qué, con
todas las condiciones relevantes: luz, nubes, luna, Vía Láctea, niebla, viento, humedad, etc.

## Decisiones ya tomadas (no reabrir)
- Frontal web tradicional desplegado en **Vercel (plan gratuito)**. **Se abandona el bot de
  Telegram con Mini App**: borra `app/`, `Dockerfile`, `requirements-bot.txt`, las referencias a
  Telegram WebApp en la web y las variables que solo usaba el bot.
- Todo gratuito y sin IA/LLM. Sin claves de pago. Flickr descartado (su API pide cuenta Pro).
- Datos: Wikimedia Commons (fotos geolocalizadas) + OpenStreetMap (nombres y miradores) +
  Open-Meteo (previsión) + cálculos astronómicos propios. Pipeline en Python (`descubrir_spots.py`,
  `condiciones.py`), reutilízalo y mejóralo.
- El cálculo diario corre en **GitHub Actions** (`.github/workflows/`), no en Vercel (los cron del
  plan gratuito son de una vez al día). Publica JSON en el repo; Vercel solo sirve la web.
- `notificar.py` (aviso por Telegram) se mantiene como extra opcional, desacoplado de la web.
  Las notificaciones push de verdad quedan para más adelante: no las implementes ahora.

## Lo que decides tú
Framework del frontal (recomendado Next.js; elige otro solo si lo justificas en `registro.md`),
estructura de datos, fórmulas de puntuación, diseño, fuentes de datos adicionales gratuitas y sin
clave, número de días de previsión, librerías. Si una API necesita un dominio que el entorno no
permite, pide añadirlo al usuario solo si no hay alternativa viable.

## Qué debe mostrar la web
**Para cada spot y cada día** una nota 0-10 por tipo de salida —amanecer, atardecer, noche
estrellada/Vía Láctea, niebla— con **desglose explicable** (qué suma y qué resta).

Condiciones diurnas: horas de amanecer y atardecer, hora dorada y azul, **azimut del sol** (y su
línea sobre el mapa desde el spot), nubes baja/media/alta, nubosidad en el horizonte hacia el sol,
visibilidad, probabilidad de lluvia.

Condiciones nocturnas: inicio y fin de la noche astronómica, **fase e iluminación de la luna**, su
salida/puesta y la ventana sin luna, **altura y azimut del núcleo de la Vía Láctea** y las horas
en que es fotografiable, nubosidad, humedad y punto de rocío (riesgo de rocío en la lente), viento,
temperatura, **contaminación lumínica del spot** (estima Bortle o equivalente; elige fuente gratuita
sin clave, p. ej. un atlas en teselas o raster VIIRS procesado una vez).

Otras: niebla y posibles mares de nubes, reflejos en agua (viento casi nulo), aviso de fiabilidad
decreciente en días lejanos.

**Del spot**: fotos de ejemplo con autor y licencia (obligatorio), tipo, orientación de la vista si
OSM la da, meses más fotografiados, enlace "Cómo llegar".

**Interfaz**: móvil primero y correcta en escritorio; mapa + ranking + ficha; filtros por día, tipo
de salida y distancia a mi ubicación; tema claro/oscuro; un **modo noche con rojo** pensado para
usarlo en el campo; carga rápida y utilizable sin JavaScript pesado. Cuida el diseño de verdad
(skill `frontend-design` si está disponible).

## Cómo trabajar (bucle obligatorio)
1. Implementa un bloque pequeño. 2. Pruébalo. 3. Lee los fallos y corrige. 4. Repite.
Commits pequeños y frecuentes a `main` con mensajes claros. Mantén `registro.md` con decisiones,
problemas encontrados y cómo se resolvieron.

## Cómo probar (no des nada por bueno sin ejecutarlo)
- **Datos reales primero**: ejecuta `descubrir_spots.py` y `condiciones.py` contra las APIs reales
  y revisa la salida. Inspecciona los 30 mejores spots: ¿son realmente paisaje? Ajusta
  `PALABRAS_PAISAJE`/`PALABRAS_EXCLUIR`, el tamaño de tesela y los umbrales hasta que salgan
  spots razonables para la Sierra de Madrid. Prueba además otra zona (p. ej. Costa da Morte).
- **Astronomía**: contrasta salida/puesta de sol y luna, fase y posición de la Vía Láctea con una
  fuente de referencia independiente (tolerancia de pocos minutos / un par de grados).
- **Notas**: tests con casos sintéticos extremos (cielo despejado y luna llena, niebla densa,
  lluvia, horizonte tapado) que comprueben que la nota se mueve en el sentido correcto.
- **Pipeline**: tests automáticos (pytest) con respuestas de API guardadas; el JSON publicado no
  debe contener `NaN` ni valores no válidos.
- **Web**: build de producción sin errores, tests end-to-end con Playwright en viewport móvil y
  de escritorio, y **revisa tú las capturas** (claro, oscuro, modo noche). Sin errores en consola.
- **Workflows**: valida el YAML y simula localmente cada paso.

## Definición de hecho
- [ ] Pipeline real funcionando con datos reales y tests en verde.
- [ ] Web con todo lo de "Qué debe mostrar", probada en móvil y escritorio.
- [ ] Notas explicables, validadas con los casos sintéticos y revisadas con datos de hoy.
- [ ] GitHub Actions actualiza los datos solos y sin fallar (primera ejecución manual correcta).
- [ ] Preparada para Vercel: `npm run build` limpio y configuración incluida.
- [ ] `README.md` y `CLAUDE.md` actualizados al estado real; `registro.md` completo.
- [ ] Sin secretos en el código.

## Cuándo parar y preguntar al usuario (solo en estos casos)
- Requiere una acción humana que no puedes hacer: conectar el repo a Vercel desde su cuenta,
  añadir un secreto en GitHub, instalar una app.
- Una decisión irreversible o que implique coste económico.
- Un bloqueo real tras varios intentos distintos: explica qué probaste.

Si algo bloquea una parte, déjala preparada, documenta el paso manual y **sigue con el resto**.

## Convenciones
Python 3.12, código, comentarios y textos de la web en español. Secretos solo por variables de
entorno. Respeta límites de APIs: caché, pausas, `maxlag` y User-Agent descriptivo en Wikimedia.
Fuentes con licencia: muestra siempre autor y licencia de las fotos de Commons y la atribución de
OpenStreetMap y Open-Meteo.
