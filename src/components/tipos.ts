import type { Momento } from "@/lib/modelo";

/** Fila del ranking y punto del mapa: lo mínimo que viaja al navegador. */
export interface FilaRanking {
  id: string;
  nombre: string;
  lat: number;
  lon: number;
  tipo: string | null;
  nota: number;
  clase: string;
  momento: Momento;
  hora: string;
  motivos: string[];
  /** fotógrafos distintos en Commons: desempata y da contexto */
  autores: number;
  dudosa: boolean;
}
