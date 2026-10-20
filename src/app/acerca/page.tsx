import type { Metadata } from "next";

export const metadata: Metadata = { title: "Cómo se puntúa" };

export default function Acerca() {
  return (
    <main className="prosa">
      <h1>Cómo se puntúa</h1>
      <p>
        Cada spot recibe cada día una nota de 0 a 10 para cuatro salidas: amanecer, atardecer, noche estrellada / Vía
        Láctea y niebla. Los modelos se basan en cómo trabajan los servicios especializados (Sunsethue, Astrospheric),
        en la física del color del cielo (NOAA) y en lo que repiten los fotógrafos, y están contrastados con datos
        históricos. En la ficha de cada spot verás qué ha sumado y qué ha restado: el desglose suma exactamente la nota.
      </p>

      <h2>Amanecer y atardecer: el camino de la luz</h2>
      <p>
        Para que el cielo se encienda hacen falta nubes que reflejen la luz y que la luz les llegue. Se evalúa el
        momento de más color: 15 minutos antes de salir el sol y 15 después de ponerse.
      </p>
      <ul>
        <li><strong>Base 3</strong>: luz rasante del sol, si llega.</li>
        <li><strong>Lienzo</strong> (hasta +7): nubes altas y medias sobre ti (60 %) y a 15-40 km hacia el sol (40 %). Lo ideal es un 40-70 %; una capa completa todavía puede “bañar de rojo” el cielo si la luz entra por debajo. Las nubes altas (cirros) cuentan el doble que las medias, que en los modelos suelen ser altostratos grises.</li>
        <li><strong>Camino del sol</strong>: nubes bajas a 15, 40, 80 y 150 km en la dirección del sol. Un banco de nubes bajas a 30-50 km basta para que no se encienda nada. Una capa media espesa lejos también corta la luz a las nubes altas.</li>
        <li><strong>Nubes bajas sobre ti</strong>: tapan el lienzo.</li>
        <li><strong>Aire</strong>: el aire limpio da colores vivos. Los aerosoles y sobre todo la <strong>calima</strong> (polvo del Sáhara) los apagan y velan el sol; la humedad alta resta; tras la lluvia el aire está lavado y suma.</li>
        <li><strong>Lluvia</strong> en el momento, visibilidad, y reflejos en el agua si no hay viento.</li>
      </ul>

      <h2>Noche estrellada y Vía Láctea</h2>
      <ul>
        <li>Se puntúa cada hora de noche astronómica (nubes y luz de luna) y cuenta la <strong>mejor ventana de 3 horas</strong>: no hace falta que toda la noche sea buena.</li>
        <li><strong>Transparencia</strong>: vapor de agua en la columna, aerosoles y humedad. Más que el “seeing”, es lo que importa para la Vía Láctea.</li>
        <li><strong>Contaminación lumínica</strong> del spot según el <a href="https://djlorenz.github.io/astronomy/lp/">atlas mundial de D. Lorenz (2025)</a>, y la <strong>cúpula de luz</strong> de las ciudades en la dirección en la que mirarás: hacia el núcleo de la Vía Láctea en temporada, o hacia el sur. El Bortle que se muestra es una equivalencia aproximada.</li>
        <li>Suma si el núcleo de la Vía Láctea está alto sin luna; restan las rachas de viento; aviso de rocío si la temperatura se acerca al punto de rocío.</li>
      </ul>

      <h2>Niebla y mar de nubes</h2>
      <ul>
        <li>
          <strong>Niebla en el spot</strong>: probabilidad calibrada con 10 años de observaciones de los aeropuertos de
          Madrid. Lo que de verdad la anuncia es la humedad máxima de madrugada (por encima del 85 %) y que el viento
          baje de unos 6 km/h; desaparece hacia 20 km/h. Ni con el aire saturado es segura: el máximo histórico es de
          ~1 de cada 2 madrugadas, así que un 50 % ya es una nota de 9. Fotogénica en embalses, ríos o bosques; en un
          mirador o una cumbre significa estar dentro de la nube y resta.
        </li>
        <li>
          <strong>Mar de nubes</strong>: con el perfil vertical del modelo (temperatura, humedad y nubes por niveles)
          en el llano se calcula el techo de la capa de nubes bajas y si hay inversión térmica encima. Si el spot queda
          por encima del techo y fuera de la niebla, es candidato a mar de nubes.
        </li>
      </ul>

      <h2>Fiabilidad y confianza</h2>
      <p>
        La previsión cubre 5 días: las nubes se predicen bien a 1-2 días, regular al tercero y mal después. Además,
        cada nota se recalcula con las nubes de un segundo modelo (ECMWF): si las dos notas difieren mucho, verás
        “previsión dudosa”. Los datos se recalculan cada 3 horas.
      </p>

      <h2>Cómo se ha validado</h2>
      <ul>
        <li>Sol, luna y Vía Láctea: contrastados con el Observatorio Naval de EE. UU. y astropy (minutos y décimas de grado).</li>
        <li>Niebla: 11 792 madrugadas de 2016-2025 en Barajas, Getafe, Cuatro Vientos y Torrejón. El modelo distingue las madrugadas con niebla con un AUC de 0,92 (1 sería perfecto, 0,5 el azar).</li>
        <li>Amanecer y atardecer: días con fotos de puestas y salidas de sol de Madrid y la Sierra en Wikimedia Commons frente al resto del mismo mes, con el tiempo real de 2016-2025. El modelo nuevo los separa mejor que el anterior (AUC 0,60 frente a 0,56; en amanecer 0,66). Es una señal ruidosa: también se fotografían puestas mediocres.</li>
      </ul>

      <h2>Fuentes</h2>
      <table>
        <tbody>
          <tr><th>Previsión</th><td><a href="https://open-meteo.com/">Open-Meteo</a> (CC BY 4.0), con ECMWF IFS como segundo modelo</td></tr>
          <tr><th>Aerosoles y polvo</th><td>CAMS (Copernicus) vía Open-Meteo</td></tr>
          <tr><th>Sol, luna y Vía Láctea</th><td>Cálculo propio (astral, Meeus)</td></tr>
          <tr><th>Contaminación lumínica</th><td><a href="https://djlorenz.github.io/astronomy/lp/">World Atlas of Artificial Night Sky Brightness 2025</a>, D. Lorenz</td></tr>
          <tr><th>Mapa y nombres</th><td>© <a href="https://www.openstreetmap.org/copyright">colaboradores de OpenStreetMap</a> (ODbL)</td></tr>
          <tr><th>Fotos</th><td><a href="https://commons.wikimedia.org/">Wikimedia Commons</a>, con la licencia de cada autor</td></tr>
        </tbody>
      </table>
    </main>
  );
}
