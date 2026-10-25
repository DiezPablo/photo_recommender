// Mar en los spots de costa (Open-Meteo Marine): pleamares y bajamares del día y, en el pico de luz, marea y
// oleaje. Informativo: no entra en la nota.

export interface MarMomento {
  olas_m: number | null;
  periodo_s: number | null;
  /** 0 = bajamar del día, 1 = pleamar (sin él, la marea apenas se nota: Mediterráneo) */
  marea?: number;
  sube?: boolean;
}

export interface Mar {
  rango_m: number;
  mareas: { t: string; tipo: "alta" | "baja"; m: number }[];
  amanecer?: MarMomento;
  atardecer?: MarMomento;
}

/** «Bajamar, subiendo», «media marea, bajando»… */
export function textoMarea(m: MarMomento): string | null {
  if (m.marea === undefined) return null;
  const nivel = m.marea <= 0.2 ? "Bajamar" : m.marea >= 0.8 ? "Pleamar" : m.marea < 0.5 ? "Marea baja" : "Marea alta";
  return m.sube === undefined ? nivel : `${nivel}, ${m.sube ? "subiendo" : "bajando"}`;
}

/** Oleaje para la foto: por debajo de medio metro, mar en calma (reflejos, larga exposición). */
export function textoOlas(m: MarMomento): string | null {
  if (m.olas_m === null) return null;
  const altura = `${m.olas_m.toLocaleString("es-ES")} m`;
  const periodo = m.periodo_s ? ` · ${m.periodo_s} s` : "";
  const calma =
    m.olas_m < 0.5 ? " (mar en calma)" : m.olas_m >= 2.5 ? " (mar fuerte: cuidado en rocas y acantilados)" : "";
  return `${altura}${periodo}${calma}`;
}
