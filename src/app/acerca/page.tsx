import type { Metadata } from "next";

export const metadata: Metadata = { title: "Cómo se puntúa" };

export default function Acerca() {
  return (
    <main className="prosa">
      <h1>Cómo se puntúa</h1>
      <p>
        Cada spot recibe cada día una nota de 0 a 10 para cuatro salidas: amanecer, atardecer, noche estrellada / Vía
        Láctea y niebla. La nota es una <strong>suma</strong>: se parte de una base y cada condición suma o resta
        puntos. En la ficha de cada spot verás exactamente qué ha sumado y qué ha restado.
      </p>

      <h2>Amanecer y atardecer</h2>
      <ul>
        <li><strong>Base 4</strong>: con cielo limpio la luz es bonita pero el cielo queda plano.</li>
        <li><strong>Lienzo de nubes altas o medias</strong> entre el 35 y el 70 %: <strong>+4</strong>. Son las que se tiñen de naranja y rojo. Si cubren casi todo, el cielo puede quedarse gris (hasta −2).</li>
        <li><strong>Nubes bajas en el spot</strong>: hasta −3; tapan el cielo.</li>
        <li><strong>Horizonte hacia el sol</strong>: se mira la nubosidad baja a 40 km en la dirección del orto u ocaso. Si hay un banco de nubes allí, el sol no ilumina las nubes desde abajo (hasta −3,5); si está despejado y hay lienzo, +1.</li>
        <li>Probabilidad de lluvia (hasta −3), visibilidad (niebla o calima restan; aire muy limpio +0,3) y, en lagos, embalses y playas, <strong>reflejos</strong> si el viento es casi nulo (+0,5).</li>
      </ul>

      <h2>Noche estrellada y Vía Láctea</h2>
      <ul>
        <li><strong>Base 10</strong> y se resta: nubosidad (hasta −9) en las horas oscuras útiles, las que no tienen luna si las hay.</li>
        <li><strong>Luna</strong>: resta según su iluminación, pero solo si no deja un rato oscuro. Con 3 horas de noche astronómica sin luna ya no resta nada.</li>
        <li><strong>Contaminación lumínica</strong> del spot, del <a href="https://djlorenz.github.io/astronomy/lp/">atlas mundial de D. Lorenz (2025, datos VIIRS)</a>: de 0 en cielos oscuros (zonas 0-2) a −6 en ciudad (zona 7). Se muestra un Bortle aproximado: el atlas mide el brillo en el cénit y Bortle es una escala visual de todo el cielo, así que es solo una equivalencia orientativa.</li>
        <li>Humedad muy alta (−0,8), viento (hasta −0,8) y <strong>+0,5</strong> si el núcleo de la Vía Láctea está a más de 10° de altura al menos una hora sin luna. Si la temperatura baja a menos de 2 °C del punto de rocío se avisa del riesgo de rocío en la lente.</li>
      </ul>

      <h2>Niebla y mar de nubes</h2>
      <p>Se evalúan dos escenarios entre 3 h antes y 1 h después del amanecer, y se queda el mejor:</p>
      <ul>
        <li>
          <strong>Niebla en el propio spot</strong>: según lo cerca que esté el aire de condensar (humedad por encima
          del 85 %, temperatura a menos de 3 °C del punto de rocío y viento flojo) suma hasta +8, y +1 si el modelo ya
          prevé visibilidad de menos de 1 km. Es fotogénica en bosques, ríos o embalses, pero en un{" "}
          <strong>mirador o una cumbre</strong> significa estar dentro de la nube sin ver nada: allí resta hasta −5,5.
          La lluvia también resta.
        </li>
        <li>
          <strong>Mar de nubes</strong>: si el spot está a más de 900 m, fuera de la niebla, y hay nubes bajas por
          debajo (en los valles y la meseta, a 40 km), base 4 y hasta +5 según cuántas haya; +1 por encima de 1500 m.
        </li>
      </ul>

      <h2>Fiabilidad</h2>
      <p>
        La previsión cubre 5 días. Las nubes se predicen razonablemente bien a 1-2 días, regular al tercero y mal a
        partir del cuarto: por eso los días lejanos llevan el aviso de fiabilidad baja. Los datos se recalculan cada 3 horas.
      </p>

      <h2>De dónde salen los spots</h2>
      <p>
        De las fotos geolocalizadas de <a href="https://commons.wikimedia.org/">Wikimedia Commons</a>: se quedan las
        de calidad reconocida o con categorías de paisaje, se agrupan por cercanía y un spot necesita fotos de varios
        autores distintos. <a href="https://www.openstreetmap.org/">OpenStreetMap</a> les da nombre y añade miradores sin
        fotos. Las fotos se muestran siempre con su autor y licencia.
      </p>

      <h2>Fuentes</h2>
      <table>
        <tbody>
          <tr><th>Previsión</th><td><a href="https://open-meteo.com/">Open-Meteo</a> (CC BY 4.0)</td></tr>
          <tr><th>Sol, luna y Vía Láctea</th><td>Cálculo propio (astral, Meeus), contrastado con el Observatorio Naval de EE. UU. y astropy</td></tr>
          <tr><th>Contaminación lumínica</th><td><a href="https://djlorenz.github.io/astronomy/lp/">World Atlas of Artificial Night Sky Brightness 2025</a>, D. Lorenz</td></tr>
          <tr><th>Mapa y nombres</th><td>© <a href="https://www.openstreetmap.org/copyright">colaboradores de OpenStreetMap</a> (ODbL)</td></tr>
          <tr><th>Fotos</th><td><a href="https://commons.wikimedia.org/">Wikimedia Commons</a>, con la licencia de cada autor</td></tr>
        </tbody>
      </table>
    </main>
  );
}
