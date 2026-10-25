// En la ficha de un spot: cuándo sale o se pone el sol (o la luna llena) justo por un pico de su horizonte.
import { cargarAlineaciones, fechaCorta, fechaLarga, textoAlineacion } from "@/features/eventos/datos";

export default function AlineacionesSpot({ id, max = 6 }: { id: string; max?: number }) {
  const datos = cargarAlineaciones();
  const lista = datos?.spots[id]?.slice(0, max);
  if (!datos || !lista?.length) return null;
  return (
    <div className="alineaciones">
      <h3>Alineaciones de los próximos meses</h3>
      <ul>
        {lista.map((a) => (
          <li key={`${a.cuerpo}-${a.fecha}-${a.azimut}`} className={`alineacion-${a.cuerpo}`}>
            <b>{fechaLarga(a.fecha, false)}</b>, {a.hora}
            {a.desde && a.hasta && a.desde !== a.hasta && (
              <small>
                {" "}
                (del {fechaCorta(a.desde)} al {fechaCorta(a.hasta)})
              </small>
            )}
            <span>{textoAlineacion(a)}.</span>
          </li>
        ))}
      </ul>
      <p className="nota-pie">
        Calculado con el perfil del terreno (modelo de elevaciones a ~30 m, cada 2°) y un margen de {datos.tolerancia}°:
        comprueba el encuadre exacto antes de ir.
      </p>
    </div>
  );
}
