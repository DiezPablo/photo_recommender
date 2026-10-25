// Posición del sol (NOAA, precisión de ~1 min entre ±72° de latitud): horas en las que el sol pasa por una
// altura dada. Puro: sirve en el servidor y en el navegador.

const RAD = Math.PI / 180;

/** Día juliano a las 0 h UTC de una fecha YYYY-MM-DD. */
function diaJuliano(fecha: string): number {
  return Date.parse(`${fecha}T00:00:00Z`) / 864e5 + 2440587.5;
}

/** Declinación (°) y ecuación del tiempo (min) para un instante en siglos julianos desde J2000. */
function solEn(t: number): { dec: number; eqt: number } {
  const l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360;
  const m = 357.52911 + t * (35999.05029 - 0.0001537 * t);
  const e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t);
  const c =
    Math.sin(m * RAD) * (1.914602 - t * (0.004817 + 0.000014 * t)) +
    Math.sin(2 * m * RAD) * (0.019993 - 0.000101 * t) +
    Math.sin(3 * m * RAD) * 0.000289;
  const lon = l0 + c - 0.00569 - 0.00478 * Math.sin((125.04 - 1934.136 * t) * RAD);
  const eps0 = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60;
  const eps = eps0 + 0.00256 * Math.cos((125.04 - 1934.136 * t) * RAD);
  const dec = Math.asin(Math.sin(eps * RAD) * Math.sin(lon * RAD)) / RAD;
  const y = Math.tan((eps / 2) * RAD) ** 2;
  const eqt =
    (4 *
      (y * Math.sin(2 * l0 * RAD) -
        2 * e * Math.sin(m * RAD) +
        4 * e * y * Math.sin(m * RAD) * Math.cos(2 * l0 * RAD) -
        0.5 * y * y * Math.sin(4 * l0 * RAD) -
        1.25 * e * e * Math.sin(2 * m * RAD))) /
    RAD;
  return { dec, eqt };
}

/**
 * Instante (UTC) en que el sol pasa por `altura` grados la mañana (`manana`) o la tarde de `fecha` en (lat, lon).
 * Altura -0,833 = salida/puesta; -6 = crepúsculo civil; 6 = fin/inicio de la hora dorada. null si no ocurre.
 */
export function horaSol(fecha: string, lat: number, lon: number, altura: number, manana: boolean): Date | null {
  // dos iteraciones: la segunda con la posición del sol a la hora aproximada
  let minutos = 720 - 4 * lon;
  for (let i = 0; i < 2; i++) {
    const t = (diaJuliano(fecha) + minutos / 1440 - 2451545) / 36525;
    const { dec, eqt } = solEn(t);
    const cosH =
      (Math.sin(altura * RAD) - Math.sin(lat * RAD) * Math.sin(dec * RAD)) /
      (Math.cos(lat * RAD) * Math.cos(dec * RAD));
    if (cosH < -1 || cosH > 1) return null;
    const h = Math.acos(cosH) / RAD;
    minutos = 720 - 4 * (lon + (manana ? h : -h)) - eqt;
  }
  return new Date(Date.parse(`${fecha}T00:00:00Z`) + minutos * 60000);
}

/** Zona horaria de un punto de España: Canarias va una hora por detrás. */
export function zonaHoraria(lon: number): string {
  return lon < -12 ? "Atlantic/Canary" : "Europe/Madrid";
}

/** "07:58" en la hora local del punto. */
export function horaLocal(d: Date, lon = -3.7): string {
  return d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit", timeZone: zonaHoraria(lon) });
}

/** Fecha YYYY-MM-DD en hora local, `dias` después de `d`. */
export function fechaLocal(d: Date, dias = 0, lon = -3.7): string {
  return new Date(d.getTime() + dias * 864e5).toLocaleDateString("sv-SE", { timeZone: zonaHoraria(lon) });
}
