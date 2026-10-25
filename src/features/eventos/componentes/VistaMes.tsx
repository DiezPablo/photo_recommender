// Un mes del calendario del paisaje: el cielo (luna, meteoros, Vía Láctea, eclipses) y el paisaje en marcha
// (floraciones, otoño, nieve, agua). La fauna tiene su propio calendario. Sin JS
// salvo el mapa.
import Link from "next/link";
import AvisoAurora from "@/features/eventos/componentes/AvisoAurora";
import MapaEventos from "@/features/eventos/componentes/MapaEventos";
import MejoresZonasMes from "@/features/clima/componentes/MejoresZonasMes";
import AlineacionesMes from "@/features/eventos/componentes/AlineacionesMes";
import TarjetaEvento from "@/features/eventos/componentes/TarjetaEvento";
import NavMeses from "@/features/eventos/componentes/NavMeses";
import {
  activoEnMes,
  ambito,
  rutaCalendario,
  anoDelMes,
  avisoAurora,
  type Categoria,
  type Eventos,
  fechaCorta,
  fechaLarga,
  MESES,
  mesDe,
  TEXTO_AURORA,
  TEXTO_CALIDAD,
} from "@/features/eventos/modelo";

const ORDEN_CATEGORIAS: Categoria[] = ["flora", "otono", "paisaje", "agua", "nieve"];

export default function VistaMes({ eventos, mes, mesHoy }: { eventos: Eventos; mes: number; mesHoy: number }) {
  const ano = anoDelMes(eventos, mes);
  const prefijo = `${ano}-${String(mes + 1).padStart(2, "0")}`;
  const lunas = eventos.luna.filter((l) => l.fecha.startsWith(prefijo));
  const meteoros = eventos.meteoros.filter((m) => m.fecha.startsWith(prefijo));
  const eclipses = eventos.eclipses.filter((e) => e.fecha.startsWith(prefijo));
  const finMes = `${prefijo}-31`;
  const ventanas = eventos.via_lactea.ventanas.filter((v) => v.desde <= finMes && v.hasta >= `${prefijo}-01`);
  const horasVl = eventos.via_lactea.horas_por_mes[mes];
  const proximoEclipse = eventos.eclipses.find((e) => e.fecha > finMes);

  const activos = eventos.naturaleza
    .filter((e) => ambito(e) === "paisaje" && activoEnMes(e, mes))
    // primero los que están en su mejor momento este mes
    .sort((a, b) => Number(mesDe(b.pico) === mes) - Number(mesDe(a.pico) === mes) || a.nombre.localeCompare(b.nombre));
  // primero los de fauna que están en su mejor momento este mes
  const fauna = eventos.naturaleza
    .filter((e) => ambito(e) === "fauna" && activoEnMes(e, mes))
    .sort((a, b) => Number(mesDe(b.pico) === mes) - Number(mesDe(a.pico) === mes));
  const porCategoria = ORDEN_CATEGORIAS.map((c) => ({ c, lista: activos.filter((e) => e.categoria === c) })).filter(
    (g) => g.lista.length,
  );

  return (
    <>
      <NavMeses mes={mes} mesHoy={mesHoy} ambito="paisaje" />

      {mes === mesHoy && <AvisoAurora aurora={avisoAurora(eventos.aurora, eventos.desde)} />}

      <div className="calendario-grid">
        <section className="seccion cielo-mes" aria-labelledby="cielo">
          <h2 className="rotulo" id="cielo">
            En el cielo · {MESES[mes]} de {ano}
          </h2>
          <ul className="lista-cielo">
            {lunas.map((l) => (
              <li key={l.fecha}>
                <span className={`icono-luna ${l.fase}`} aria-hidden />
                <div>
                  <b>Luna {l.fase}</b> · {fechaLarga(l.fecha, false)}
                  <small>
                    {l.fase === "nueva"
                      ? "Las noches de alrededor son las más oscuras del mes."
                      : "Sale al atardecer por el este: momento para la luna sobre el paisaje."}
                  </small>
                </div>
              </li>
            ))}
            {ventanas.map((v) => (
              <li key={v.luna_nueva}>
                <span className="icono-vl" aria-hidden />
                <div>
                  <b>Vía Láctea sin luna</b> · del {fechaCorta(v.desde)} al {fechaCorta(v.hasta)}
                  <small>Hasta {v.horas_max.toLocaleString("es-ES")} h de núcleo alto en noche cerrada.</small>
                </div>
              </li>
            ))}
            {!ventanas.length && (
              <li>
                <span className="icono-vl apagado" aria-hidden />
                <div>
                  <b>Vía Láctea</b>
                  <small>
                    {horasVl < 0.5
                      ? "El núcleo no se ve de noche este mes: temporada de marzo a septiembre."
                      : `El núcleo asoma unas ${horasVl.toLocaleString("es-ES")} h por noche, sin ventana sin luna.`}
                  </small>
                </div>
              </li>
            )}
            {meteoros.map((m) => (
              <li key={m.id}>
                <span className={`icono-meteoro ${m.calidad}`} aria-hidden />
                <div>
                  <b>{m.nombre}</b> · noche del {fechaCorta(m.noche)} al {fechaCorta(m.fecha)}
                  <small>
                    Hasta {m.thz} meteoros/h en condiciones ideales. {TEXTO_CALIDAD[m.calidad]} (luna al{" "}
                    {m.luna.iluminacion} %). {m.descripcion}
                  </small>
                </div>
              </li>
            ))}
            {mes === mesHoy && eventos.aurora && (
              <li>
                <span className={`icono-aurora ${eventos.aurora.nivel}`} aria-hidden />
                <div>
                  <b>Auroras</b> · próximas tres noches
                  <small>
                    {TEXTO_AURORA[eventos.aurora.nivel]}: índice Kp máximo previsto{" "}
                    {eventos.aurora.kp_max.toLocaleString("es-ES")} (hacen falta 7 en el norte y 8 en el resto).
                  </small>
                </div>
              </li>
            )}
            {eclipses.map((e) => (
              <li key={e.id} className="eclipse">
                <span className="icono-eclipse" aria-hidden />
                <div>
                  <b>{e.nombre}</b> · {fechaLarga(e.fecha, false)}
                  <small>
                    {e.descripcion} {e.consejo}{" "}
                    <a href={e.fuente} rel="noopener">
                      Mapa del IGN
                    </a>
                  </small>
                </div>
              </li>
            ))}
          </ul>
          {proximoEclipse && !eclipses.length && (
            <p className="nota-pie">
              Próximo gran eclipse: {proximoEclipse.nombre.toLowerCase()} el {fechaLarga(proximoEclipse.fecha)}.
            </p>
          )}
        </section>

        <section className="seccion mapa-mes" aria-label={`Mapa de eventos de ${MESES[mes]}`}>
          <MapaEventos
            eventos={activos.map((e) => ({
              id: e.id,
              nombre: e.nombre,
              lat: e.lat,
              lon: e.lon,
              radio_km: e.radio_km,
              categoria: e.categoria,
            }))}
            etiqueta={`Mapa de eventos de ${MESES[mes]}`}
          />
        </section>
      </div>

      <MejoresZonasMes mes={mes} />
      <AlineacionesMes eventos={eventos} mes={mes} />

      {fauna.length > 0 && (
        <Link href={rutaCalendario("fauna", mes)} className="aviso-fauna">
          <b>Fauna en {MESES[mes]}</b>:{" "}
          {fauna
            .map((e) => e.nombre)
            .slice(0, 3)
            .join(", ")}
          {fauna.length > 3 && ` y ${fauna.length - 3} más`} → calendario de fauna
        </Link>
      )}

      <section className="naturaleza-mes" aria-labelledby="naturaleza">
        <h2 className="rotulo" id="naturaleza">
          En el paisaje · {activos.length} {activos.length === 1 ? "evento" : "eventos"}
        </h2>
        {porCategoria.map(({ c, lista }) => (
          <div key={c} className="grupo-categoria">
            <h3 className={`titulo-categoria cat-${c}`}>
              <span className="punto-cat" aria-hidden /> {eventos.categorias[c]}
            </h3>
            <div className="rejilla-eventos">
              {lista.map((e) => (
                <TarjetaEvento key={e.id} evento={e} categorias={eventos.categorias} mes={mes} />
              ))}
            </div>
          </div>
        ))}
        {!activos.length && <p>Ningún evento de la lista este mes.</p>}
        <p className="nota-pie">
          Fechas habituales: cada año cambian con el tiempo (un invierno frío retrasa la floración, una sequía deja las
          lagunas sin aves). Confirma antes de ir con el parque o la oficina de turismo.
        </p>
      </section>
    </>
  );
}
