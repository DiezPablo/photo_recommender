"use client";
// Base común de los mapas: Leaflet se carga después de pintar la página (import dinámico), así que el
// contenido se usa sin esperar al mapa ni descargar Leaflet si no hay JavaScript.
import type { LayerGroup, Map as LMap, MapOptions } from "leaflet";
import { useEffect, useRef, useState } from "react";
import { controlSatelite } from "@/ui/mapa/satelite";

export type Leaflet = typeof import("leaflet");

export interface MapaBase {
  /** contenedor donde se monta el mapa */
  caja: React.RefObject<HTMLDivElement | null>;
  mapa: React.RefObject<LMap | null>;
  /** el módulo de Leaflet, ya cargado (null hasta que el mapa está listo) */
  leaflet: React.RefObject<Leaflet | null>;
  listo: boolean;
  /** cambia al cambiar de tema: los colores salen de variables CSS y hay que repintar */
  tema: number;
  /** cambia cada vez que el usuario mueve o acerca el mapa */
  vista: number;
  /** crea una capa nueva sobre el mapa (en el orden de llamada) */
  nuevaCapa: () => LayerGroup;
}

export function useMapaBase(opciones: MapOptions = {}): MapaBase {
  const caja = useRef<HTMLDivElement>(null);
  const mapa = useRef<LMap | null>(null);
  const leaflet = useRef<Leaflet | null>(null);
  const [listo, setListo] = useState(false);
  const [tema, setTema] = useState(0);
  const [vista, setVista] = useState(0);

  useEffect(() => {
    let cancelado = false;
    (async () => {
      const L = (await import("leaflet")).default;
      await import("leaflet/dist/leaflet.css");
      if (cancelado || !caja.current || mapa.current) return;
      const m = L.map(caja.current, { zoomControl: true, attributionControl: true, ...opciones });
      // Teselas estándar de OSM (CARTO ya pide clave); en los temas oscuros se tiñen con CSS
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        className: "capa-base",
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(m);
      // sin la bandera de colores del prefijo (rompería el modo noche)
      m.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
      m.on("moveend", () => setVista((v) => v + 1));
      controlSatelite(L, m);
      leaflet.current = L;
      mapa.current = m;
      setListo(true);
    })();
    const alCambiarTema = () => setTema((t) => t + 1);
    window.addEventListener("tema", alCambiarTema);
    return () => {
      cancelado = true;
      window.removeEventListener("tema", alCambiarTema);
      mapa.current?.remove();
      mapa.current = null;
    };
    // las opciones solo cuentan al crear el mapa
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const nuevaCapa = () => leaflet.current!.layerGroup().addTo(mapa.current!);
  return { caja, mapa, leaflet, listo, tema, vista, nuevaCapa };
}

/** Color de una variable CSS («var(--sol)» → «#e3a020»): Leaflet pinta en canvas y no entiende variables. */
export function colorCss(v: string): string {
  const m = v.match(/^var\((--[\w-]+)\)$/);
  return m ? getComputedStyle(document.documentElement).getPropertyValue(m[1]).trim() || "#888" : v;
}

export function escaparHtml(s: string): string {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);
}
