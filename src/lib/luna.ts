// Iluminación de la luna (Meeus, Astronomical Algorithms, cap. 48, baja precisión: error < 1 %), igual que
// rasante.cielo.astro.iluminacion_luna. Pura.

const RAD = Math.PI / 180;

/** Fracción iluminada (0-1) en un instante. */
export function iluminacionLuna(t: Date): number {
  const jd = t.getTime() / 864e5 + 2440587.5;
  const T = (jd - 2451545.0) / 36525;
  const D = (297.8501921 + 445267.1114034 * T) % 360;
  const M = (357.5291092 + 35999.0502909 * T) % 360;
  const Mp = (134.9633964 + 477198.8675055 * T) % 360;
  const i =
    180 -
    D -
    6.289 * Math.sin(Mp * RAD) +
    2.1 * Math.sin(M * RAD) -
    1.274 * Math.sin((2 * D - Mp) * RAD) -
    0.658 * Math.sin(2 * D * RAD) -
    0.214 * Math.sin(2 * Mp * RAD) -
    0.11 * Math.sin(D * RAD);
  return (1 + Math.cos(i * RAD)) / 2;
}

/** Iluminación a medianoche (hora peninsular) de la noche que empieza la tarde de `fecha`. */
export function lunaDeLaNoche(fecha: string): number {
  return iluminacionLuna(new Date(Date.parse(`${fecha}T23:00:00Z`)));
}
