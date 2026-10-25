"use client";
// Mapa del calendario: el área de cada evento (círculo con su radio) y, en la página de un evento, los spots
// y las salidas de rutas cercanas.
import type { LayerGroup } from "leaflet";
import { useEffect, useRef } from "react";
import { colorCss, escaparHtml as esc, useMapaBase } from "@/ui/mapa/useMapaBase";

export interface PuntoEvento {
  id: string;
  nombre: string;
  lat: number;
  lon: number;
  radio_km: number;
  categoria: string;
  /** a dónde lleva su ventana; null, a ninguna (por defecto, `${enlace}/${id}`) */
  href?: string | null;
}
export interface PuntoSimple {
  id: string;
  nombre: string;
  lat: number;
  lon: number;
}

const NADA: PuntoSimple[] = [];

export default function MapaEventos({
  eventos,
  spots = NADA,
  rutas = NADA,
  etiqueta = "Mapa de eventos",
  enlace = "/evento",
  mundo = false,
}: {
  eventos: PuntoEvento[];
  spots?: PuntoSimple[];
  rutas?: PuntoSimple[];
  etiqueta?: string;
  /** a dónde lleva cada área («/evento», «/fauna») */
  enlace?: string;
  /** puntos de todo el mundo: se encuadran todos (sin el recorte a la península) */
  mundo?: boolean;
}) {
  const { caja, mapa, leaflet, listo, tema, nuevaCapa } = useMapaBase({ scrollWheelZoom: false });
  const capa = useRef<LayerGroup | null>(null);

  useEffect(() => {
    if (!listo || !mapa.current || !leaflet.current) return;
    const L = leaflet.current;
    capa.current ??= nuevaCapa();
    const g = capa.current;
    g.clearLayers();
    const limites: [number, number][] = [];
    const solo = eventos.length === 1;
    for (const e of eventos) {
      const color = colorCss(`var(--c-${e.categoria})`);
      const area = L.circle([e.lat, e.lon], {
        radius: e.radio_km * 1000,
        color,
        weight: solo ? 2 : 1,
        fillColor: color,
        fillOpacity: solo ? 0.08 : 0.18,
      }).addTo(g);
      const centro = L.circleMarker([e.lat, e.lon], {
        radius: solo ? 7 : 6,
        weight: 2,
        color: colorCss("var(--superficie)"),
        fillColor: color,
        fillOpacity: 1,
      }).addTo(g);
      if (!solo) {
        const href = e.href === undefined ? `${enlace}/${encodeURIComponent(e.id)}` : e.href;
        const html = `<strong>${esc(e.nombre)}</strong>${href ? `<br><a href="${href}">Ver →</a>` : ""}`;
        area.bindPopup(html);
        centro.bindPopup(html);
      }
      // el círculo a mano: getBounds() de Leaflet necesita que el mapa ya tenga vista
      const dLat = e.radio_km / 111;
      const dLon = dLat / Math.cos((e.lat * Math.PI) / 180);
      limites.push([e.lat - dLat, e.lon - dLon], [e.lat + dLat, e.lon + dLon]);
    }
    for (const s of spots) {
      L.circleMarker([s.lat, s.lon], {
        radius: 5,
        weight: 1,
        color: colorCss("var(--superficie)"),
        fillColor: colorCss("var(--n-top)"),
        fillOpacity: 1,
      })
        .bindPopup(`<strong>${esc(s.nombre)}</strong><br><a href="/spot/${encodeURIComponent(s.id)}">Ver spot →</a>`)
        .addTo(g);
      limites.push([s.lat, s.lon]);
    }
    for (const r of rutas) {
      const icono = L.divIcon({ className: "", html: '<div class="salida-ruta"></div>', iconSize: [10, 10] });
      L.marker([r.lat, r.lon], { icon: icono, title: r.nombre, alt: r.nombre })
        .bindPopup(`<strong>${esc(r.nombre)}</strong><br><a href="/ruta/${encodeURIComponent(r.id)}">Ver ruta →</a>`)
        .addTo(g);
      limites.push([r.lat, r.lon]);
    }
    // con Canarias el encuadre se aleja hasta Marruecos: en el mapa general se encuadra la península
    const peninsula = limites.filter(([la]) => la > 34);
    const encuadre = !solo && !mundo && peninsula.length ? peninsula : limites;
    if (encuadre.length)
      // sin animación: si el usuario sale de la página o cambia el filtro a mitad de zoom, Leaflet falla
      // al desmontar el mapa animándose (`_leaflet_pos`)
      mapa.current.fitBounds(L.latLngBounds(encuadre), { padding: [24, 24], maxZoom: 11, animate: false });
    else mapa.current.setView([40.2, -3.7], 5, { animate: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listo, eventos, spots, rutas, tema, enlace, mundo]);

  return (
    <div ref={caja} className="mapa-caja" role="region" aria-label={etiqueta} data-listo={listo ? "si" : "no"}>
      {!listo && <div className="mapa-vacio">Cargando mapa…</div>}
    </div>
  );
}
