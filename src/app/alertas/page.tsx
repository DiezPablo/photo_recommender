import type { Metadata } from "next";
import Link from "next/link";
import { NOTA_ALERTA, SITIO, zonas } from "@/features/alertas/calendarios";

export const metadata: Metadata = {
  title: "Avisos en tu calendario",
  description:
    "Suscríbete gratis, sin cuenta, al calendario de tu zona: los mejores amaneceres, atardeceres, noches y nieblas previstos, y el calendario del cielo y la naturaleza.",
};

export default function PaginaAlertas() {
  const host = SITIO.replace(/^https?:\/\//, "");
  return (
    <main className="calendario alertas">
      <header className="titular">
        <p className="rotulo">Avisos · gratis y sin cuenta</p>
        <h1>Los mejores momentos, en tu calendario</h1>
        <p className="entradilla">
          Suscríbete al calendario de tu zona desde el móvil o el ordenador. Aparecerán los momentos con nota de{" "}
          {NOTA_ALERTA} o más en los próximos días (con la hora y el porqué), las lunas, las lluvias de meteoros, las
          noches de Vía Láctea y los eventos del paisaje y de la fauna. Se actualiza solo, dos veces al día.
        </p>
      </header>

      <section className="seccion">
        <h2 className="rotulo">Elige tu zona</h2>
        <ul className="lista-zonas">
          {zonas().map((z) => (
            <li key={z.slug}>
              <span>{z.nombre}</span>
              <a className="boton" href={`webcal://${host}/alertas/${z.slug}.ics`}>
                Suscribirse
              </a>
              <a href={`/alertas/${z.slug}.ics`} className="enlace-ics" download>
                .ics
              </a>
            </li>
          ))}
        </ul>
      </section>

      <section className="seccion">
        <h2 className="rotulo">Cómo se añade</h2>
        <ul className="pasos">
          <li>
            <b>iPhone, iPad y Mac:</b> toca «Suscribirse» y confirma en Calendario.
          </li>
          <li>
            <b>Google Calendar:</b> en el ordenador, «Otros calendarios» → «+» → «Desde URL», y pega la dirección del
            enlace «.ics» (mantén pulsado para copiarla). Google lo refresca cada pocas horas.
          </li>
          <li>
            <b>Outlook:</b> «Agregar calendario» → «Suscribirse desde la web» con la misma dirección.
          </li>
        </ul>
        <p className="nota-pie">
          Las previsiones a cuatro o cinco días pueden cambiar: el calendario las corrige en cada actualización. Para un
          spot concreto, mira su <Link href="/">ficha</Link>.
        </p>
      </section>
    </main>
  );
}
