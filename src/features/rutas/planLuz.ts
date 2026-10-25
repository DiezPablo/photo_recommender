// «Sal a las…»: a qué hora salir para estar arriba con la mejor luz y cuánto se baja de noche. Puro.
import { horaSol } from "@/lib/sol";

/** Margen sobre el tiempo MIDE (que no cuenta paradas): fotos, agua, el último repecho. */
export const MARGEN = 1.15;
const MIN = 60000;

export interface PlanMomento {
  /** salida desde el inicio de la ruta */
  salida: Date;
  /** llegada arriba */
  llegada: Date;
  /** salida o puesta del sol */
  sol: Date;
  /** minutos de marcha sin luz natural (antes del alba o después del crepúsculo civil) */
  minutosDeNoche: number;
  /** atardecer: vuelta a la salida si se empieza a bajar al acabar el color */
  regreso?: Date;
}

export interface PlanDia {
  fecha: string;
  amanecer: PlanMomento | null;
  atardecer: PlanMomento | null;
}

/** Redondea hacia abajo a múltiplos de 5 minutos: una hora de salida «de reloj». */
function aCinco(d: Date): Date {
  return new Date(Math.floor(d.getTime() / (5 * MIN)) * 5 * MIN);
}

export function planDia(fecha: string, lat: number, lon: number, horasSubida: number, horasBajada: number): PlanDia {
  const subida = horasSubida * MARGEN * 60 * MIN;
  const bajada = horasBajada * MARGEN * 60 * MIN;

  let amanecer: PlanMomento | null = null;
  const sale = horaSol(fecha, lat, lon, -0.833, true);
  const alba = horaSol(fecha, lat, lon, -6, true);
  if (sale && alba) {
    // el cielo coge color unos 30 min antes de salir el sol: hay que estar arriba para entonces
    const llegada = new Date(sale.getTime() - 30 * MIN);
    const salida = aCinco(new Date(llegada.getTime() - subida));
    amanecer = {
      salida,
      llegada,
      sol: sale,
      minutosDeNoche: Math.max(0, Math.round((Math.min(alba.getTime(), llegada.getTime()) - salida.getTime()) / MIN)),
    };
  }

  let atardecer: PlanMomento | null = null;
  const pone = horaSol(fecha, lat, lon, -0.833, false);
  const noche = horaSol(fecha, lat, lon, -6, false);
  const dorada = horaSol(fecha, lat, lon, 6, false);
  if (pone && noche) {
    // arriba al empezar la hora dorada (o 45 min antes de la puesta si el sol no llega a 6°)
    const inicio = dorada && dorada < pone ? dorada : new Date(pone.getTime() - 45 * MIN);
    const llegada = new Date(Math.min(inicio.getTime(), pone.getTime() - 45 * MIN));
    const salida = aCinco(new Date(llegada.getTime() - subida));
    // se baja cuando acaba el color, unos 20 min después de la puesta
    const regreso = new Date(pone.getTime() + 20 * MIN + bajada);
    atardecer = {
      salida,
      llegada,
      sol: pone,
      regreso,
      minutosDeNoche: Math.max(0, Math.round((regreso.getTime() - noche.getTime()) / MIN)),
    };
  }
  return { fecha, amanecer, atardecer };
}
