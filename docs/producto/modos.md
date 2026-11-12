# Los dos modos: pantallas mínimas y recorridos

Deriva de `vision.md` y de la spec 001. Regla: **seis plantillas de pantalla para los dos modos**; cada una
responde una sola pregunta. Lo que no ayude a responderla, sobra (poda de 001 §6).

## La consulta
Todo parte de tres datos, siempre en la URL (funciona sin JS, decisión 0014):
**cuándo** (hoy · esta tarde · finde · fechas · mes) · **dónde** (cerca de mí + radio · comunidad · toda España)
· **qué** (Luz · Fauna · un evento · una especie). Ninguno es obligatorio salvo "cuándo" o "qué".

## Pantallas

| # | Pantalla | Pregunta que responde | Luz: datos | Fauna: datos |
|---|---|---|---|---|
| 1 | **Portada** | "¿Cuándo tienes tiempo y qué te apetece?" | Mejor plan de hoy cerca; eventos de cielo próximos (`informe`, `eventos`) | Qué está en temporada este mes (`eventos` de fauna, cuadrícula del mes) |
| 2 | **Resultados** (lista + mapa) | "¿A qué lugar voy en ese momento?" | Lugares ordenados por nota del momento: previsión ≤ 5 días (`informe`); después, climatología del mes × idoneidad del lugar (`clima`, `lugares`) | Lugares ordenados por lo que se espera ver: especies del mes en sus cuadrículas, franja del día, tiempo previsto, distancia (`lugares`, cuadrícula, actividad, previsión) |
| 3 | **Ficha de lugar** (una plantilla, bloques por modo) | "¿Por qué aquí, a qué hora y qué me encuentro?" | Nota con desglose, hora real de sol sobre el relieve, hacia dónde abre el horizonte, oscuridad del cielo, foto, acceso | Especies de la época con fiabilidad, mejor franja, visto hace poco, hides, normas, acceso |
| 4 | **Ficha de evento o especie** | "¿Dónde y cuándo veo esto?" | Evento de cielo o de paisaje: fechas, luna, lugares donde mejor se ve | Evento de fauna o especie: temporada, lugares por fiabilidad, franja, normas |
| 5 | **Calendario** | "¿Qué viene y cuándo merece la pena?" | Luna, meteoros, Vía Láctea, eclipses, floraciones, otoño | Berrea, grullas, celos, pasos migratorios |
| 6 | **Plan** (varios días) | "¿Cómo reparto el finde o el viaje?" | Por día: amanecer, atardecer y noche con su lugar | Por día: lugar de fauna y franja; eventos en marcha |

Fuera de las seis: Método (cómo se puntúa), Normas, Hides (catálogo) y Sin conexión son páginas de apoyo.
`/rutas`, dron, logística, alineaciones y mareas dependen de la poda (backlog, "Después").

## Recorridos

### 1. "Tengo esta tarde en Madrid" (una tarde · modo sin elegir)
1. Portada → "Esta tarde" + "Cerca de mí" → **Resultados** con dos pestañas.
2. Luz: atardecer de hoy a ≤ 100 km por nota (`informe`). Fauna: lugares a ≤ 60 km con las especies de noviembre
   activas por la tarde y sin lluvia.
3. **Ficha de lugar**: hora a la que hay que estar, por qué (desglose) y aparcamiento.
- Existe: ranking con "cerca de mí", ficha de spot. Falta: la consulta común (012), pestaña Fauna (011, tras
  006-008), distancia como criterio visible (solo km en línea recta; sin rutas por carretera).

### 2. "Finde en Asturias en octubre" (un finde · ambos · fuera de previsión)
1. Portada → fechas + Asturias → **Plan** de dos días.
2. Cada día: amanecer, atardecer y noche con el lugar que mejor suele ir en octubre (climatología × idoneidad) y un
   lugar de fauna con lo que se ve en octubre; arriba, lo que está en temporada (otoño en hayedos, berrea, osos).
3. Al entrar en los 5 días de previsión, el mismo plan se recalcula con notas reales.
- Existe: `/viaje` (climatología, eventos, penalización por distancia). Falta: idoneidad estática del lugar
  (013), fauna desde la cuadrícula (006-007), quitar del plan lo podado (016).

### 3. "Quiero la berrea" (un evento · Fauna · sin fecha ni lugar)
1. Portada o Calendario → **Ficha de evento** "Berrea".
2. Responde: cuándo (ventana y pico habituales), dónde (lista de lugares de toda España ordenable por cercanía),
   mejor franja (amanecer y atardecer), fiabilidad, hides y normas.
3. Elegido lugar → **Ficha de lugar**; si la fecha está en previsión, tiempo previsto.
- Existe: eventos de fauna con **un** punto y radio (`eventos_naturaleza.csv`), fenómenos en safari_recommender.
  Falta: evento → varios lugares (014), hides y normas (011).

### 4. "Perseidas con Vía Láctea" (un evento · Luz · fecha fija)
1. Calendario → **Ficha de evento** "Perseidas": noche del máximo, luna esa noche, horas de Vía Láctea.
2. "¿Dónde verlas?" → **Resultados** de noche para esa fecha y mi zona: cielo oscuro, horizonte abierto hacia
   donde está el núcleo, noches despejadas habituales en agosto; con previsión, nota real de la noche.
3. **Ficha de lugar**: ventana sin luna, oscuridad, acceso.
- Existe: evento con luna calculada, nota de noche a 5 días, climatología de noches despejadas. Falta: resultados
  para una fecha fuera de previsión (013) y enlazarlos desde el evento de cielo (015).

## Qué sale de aquí
Specs 003 (esquema de lugar) y 012-016, en el backlog. La 010 pasa a ser la ficha de lugar única.
