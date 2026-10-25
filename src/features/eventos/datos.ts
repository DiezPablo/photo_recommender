// Lectura de public/datos/eventos.json en el build (solo servidor) y cruces con spots y rutas.
import "server-only";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { cargar } from "@/features/spots/datos";
import { cargarRutas, filaRuta, type FilaRuta } from "@/features/rutas/datos";
import { distanciaKm, type EventoNaturaleza, type Eventos } from "@/features/eventos/modelo";

export * from "@/features/eventos/modelo";

let cache: Eventos | null | undefined;

export function cargarEventos(): Eventos | null {
  if (cache !== undefined) return cache;
  const f = path.join(process.cwd(), "public", "datos", "eventos.json");
  cache = existsSync(f) ? (JSON.parse(readFileSync(f, "utf8")) as Eventos) : null;
  return cache;
}

export function getEvento(id: string): EventoNaturaleza | undefined {
  return cargarEventos()?.naturaleza.find((e) => e.id === id);
}

/** Eventos de naturaleza cuyo entorno incluye el punto (su radio más un margen para acercarse). */
export function eventosCerca(lat: number, lon: number, margenKm = 15): (EventoNaturaleza & { km: number })[] {
  return (cargarEventos()?.naturaleza ?? [])
    .map((e) => ({ ...e, km: distanciaKm(e, { lat, lon }) }))
    .filter((e) => e.km <= e.radio_km + margenKm)
    .sort((a, b) => a.km - b.km);
}

export interface SpotCercano {
  id: string;
  nombre: string;
  tipo: string | null;
  lat: number;
  lon: number;
  km: number;
}

/** Spots dentro del área del evento o a poca distancia, del más cercano al más lejano. */
export function spotsCerca(e: EventoNaturaleza, n = 8): SpotCercano[] {
  return cargar()
    .spots.map((s) => ({ id: s.id, nombre: s.nombre, tipo: s.tipo, lat: s.lat, lon: s.lon, km: distanciaKm(e, s) }))
    .filter((s) => s.km <= e.radio_km + 15)
    .sort((a, b) => a.km - b.km)
    .slice(0, n);
}

/** Rutas que salen dentro del área del evento: primero las oficiales y señalizadas, luego las más cercanas. */
export function rutasCerca(e: EventoNaturaleza, n = 8): (FilaRuta & { kmEvento: number })[] {
  return cargarRutas()
    .rutas.map((r) => {
      const f = filaRuta(r);
      return { ...f, kmEvento: distanciaKm(e, f) };
    })
    .filter((r) => r.kmEvento <= e.radio_km + 10)
    .sort((a, b) => b.rel - a.rel || a.kmEvento - b.kmEvento)
    .slice(0, n);
}
