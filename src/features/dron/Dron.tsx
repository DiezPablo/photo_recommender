// «Dron»: si se puede volar en el spot según las zonas UAS de ENAIRE y los espacios protegidos. Orientativo: antes
// de volar hay que consultar la aplicación oficial de ENAIRE.
import { CAPA, dronDe, TEXTO_NIVEL } from "@/features/dron/datos";

const RESUMEN = {
  no: "El spot está en una zona donde no se puede volar sin una autorización expresa (aeropuerto, zona militar, parque nacional…).",
  permiso: "Se puede volar pidiendo antes permiso o las condiciones al gestor de la zona.",
  condiciones: "Se puede volar respetando las condiciones de la zona (altura máxima, época de cría…).",
  libre:
    "No hay zonas geográficas de UAS ni espacios protegidos en este punto: se aplican las normas generales de la categoría abierta.",
} as const;

export function SelloDron({ id }: { id: string }) {
  const d = dronDe(id);
  if (!d) return null;
  return (
    <div title="Según ENAIRE y los espacios protegidos; consulta siempre la app oficial antes de volar">
      <dt>Dron</dt>
      <dd>
        <a href="#dron" className={`sello-dron dron-${d.estado}`}>
          {TEXTO_NIVEL[d.estado]}
        </a>
      </dd>
    </div>
  );
}

export default function Dron({ id }: { id: string }) {
  const d = dronDe(id);
  if (!d) return null;
  return (
    <section className="seccion dron" id="dron">
      <h2 className="rotulo">Volar un dron</h2>
      <p>
        <span className={`sello-dron dron-${d.estado}`}>{TEXTO_NIVEL[d.estado]}</span> {RESUMEN[d.estado]}
      </p>
      {d.zonas.length > 0 && (
        <ul className="zonas-dron">
          {d.zonas.map((z, i) => (
            <li key={i}>
              <details>
                <summary>
                  <span className={`punto-dron dron-${z.nivel}`} aria-hidden /> <b>{z.nombre ?? CAPA[z.capa]}</b>{" "}
                  <small>
                    {CAPA[z.capa]}
                    {z.desde_m ? ` · sin coordinar por debajo de ${z.desde_m} m` : ""}
                  </small>
                </summary>
                <p className="texto-dron">{z.texto}</p>
              </details>
            </li>
          ))}
        </ul>
      )}
      <p className="nota-pie">
        Siempre: categoría abierta como máximo a 120 m del suelo, con el dron a la vista, lejos de personas y con el
        registro de operador de AESA. Sobre núcleos urbanos hay que comunicarlo antes al Ministerio del Interior.
        Orientativo, con datos del{" "}
        {new Date(`${d.fecha}T12:00:00Z`).toLocaleDateString("es-ES", {
          day: "numeric",
          month: "long",
          year: "numeric",
        })}
        : antes de volar consulta{" "}
        <a href="https://drones.enaire.es/" target="_blank" rel="noopener">
          ENAIRE Drones ↗
        </a>{" "}
        y la normativa del espacio natural.
      </p>
    </section>
  );
}
