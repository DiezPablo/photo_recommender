// Asociaciones oficiales de operadores de safari por país (nombre del país como lo da Wikidata en español). Sus
// miembros tienen licencia y se comprometen a un código de conducta; algunas tienen fondo de garantía.
// Solo las conocidas y con web comprobada: en el resto, la guía explica cómo comprobar la licencia.

export interface Asociacion {
  sigla: string;
  nombre: string;
  url: string;
}

export const ASOCIACIONES: Record<string, Asociacion> = {
  Kenia: { sigla: "KATO", nombre: "Kenya Association of Tour Operators", url: "https://katokenya.org/" },
  Tanzania: { sigla: "TATO", nombre: "Tanzania Association of Tour Operators", url: "https://www.tatotz.org/" },
  Uganda: { sigla: "AUTO", nombre: "Association of Uganda Tour Operators", url: "https://www.auto.or.ug/" },
  Ruanda: { sigla: "RTTA", nombre: "Rwanda Tours and Travel Association", url: "https://www.rtta.rw/" },
  Sudáfrica: {
    sigla: "SATSA",
    nombre: "Southern Africa Tourism Services Association",
    url: "https://www.satsa.com/",
  },
  Namibia: { sigla: "TASA", nombre: "Tour and Safari Association of Namibia", url: "https://www.tasa.na/" },
  Botsuana: { sigla: "HATAB", nombre: "Hospitality and Tourism Association of Botswana", url: "https://www.hatab.bw/" },
  India: { sigla: "IATO", nombre: "Indian Association of Tour Operators", url: "https://www.iato.in/members" },
};

export function asociacionDe(pais: string | null | undefined): Asociacion | undefined {
  if (!pais) return undefined;
  // «Sudáfrica y Botsuana» (Kgalagadi): la del primer país
  return ASOCIACIONES[pais] ?? ASOCIACIONES[pais.split(" y ")[0]];
}
