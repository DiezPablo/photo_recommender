"use client";
// Mapa Leaflet. Se carga después de pintar la página (import dinámico), así que el ranking y la
// ficha se pueden usar sin esperar al mapa ni descargar Leaflet si no hay JavaScript.
import { useEffect, useRef, useState } from "react";
import type { Map as LMap, LayerGroup } from "leaflet";
import { leerUbicacion, type Ubicacion } from "@/lib/ubicacion";

export interface PuntoMapa {
  id: string;
  nombre: string;
  lat: number;
  lon: number;
  nota?: number;
  clase?: string;
  texto?: string;
}

export interface LineaMapa {
  azimut: number;
  km: number;
  color: string; // variable CSS, p. ej. "var(--sol)"
  etiqueta: string;
  discontinua?: boolean;
}

function destino(lat: number, lon: number, az: number, km: number): [number, number] {
  const r = Math.PI / 180;
  const d = km / 6371;
  const b = az * r;
  const la1 = lat * r;
  const lo1 = lon * r;
  const la2 = Math.asin(Math.sin(la1) * Math.cos(d) + Math.cos(la1) * Math.sin(d) * Math.cos(b));
  const lo2 = lo1 + Math.atan2(Math.sin(b) * Math.sin(d) * Math.cos(la1), Math.cos(d) - Math.sin(la1) * Math.sin(la2));
  return [la2 / r, lo2 / r];
}

function colorCss(v: string): string {
  const m = v.match(/^var\((--[\w-]+)\)$/);
  return m ? getComputedStyle(document.documentElement).getPropertyValue(m[1]).trim() || "#888" : v;
}

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

export default function Mapa({
  puntos,
  lineas = [],
  zoom,
  enlazar = true,
  etiqueta = "Mapa de spots",
}: {
  puntos: PuntoMapa[];
  lineas?: LineaMapa[];
  zoom?: number;
  enlazar?: boolean;
  etiqueta?: string;
}) {
  const caja = useRef<HTMLDivElement>(null);
  const mapa = useRef<LMap | null>(null);
  const capa = useRef<LayerGroup | null>(null);
  const [listo, setListo] = useState(false);
  const [ubic, setUbic] = useState<Ubicacion | null>(null);
  const [tema, setTema] = useState(0);

  // Crear el mapa una vez
  useEffect(() => {
    let cancelado = false;
    (async () => {
      const L = (await import("leaflet")).default;
      await import("leaflet/dist/leaflet.css");
      if (cancelado || !caja.current || mapa.current) return;
      const m = L.map(caja.current, { zoomControl: true, attributionControl: true, scrollWheelZoom: !enlazar ? false : true });
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 18,
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(m);
      // sin la bandera de colores del prefijo (rompería el modo noche)
      m.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
      capa.current = L.layerGroup().addTo(m);
      mapa.current = m;
      setListo(true);
    })();
    setUbic(leerUbicacion());
    const fu = (e: Event) => setUbic((e as CustomEvent<Ubicacion | null>).detail);
    const ft = () => setTema((t) => t + 1);
    window.addEventListener("ubicacion", fu);
    window.addEventListener("tema", ft);
    return () => {
      cancelado = true;
      window.removeEventListener("ubicacion", fu);
      window.removeEventListener("tema", ft);
      mapa.current?.remove();
      mapa.current = null;
    };
  }, [enlazar]);

  // Pintar puntos, líneas y ubicación
  useEffect(() => {
    if (!listo || !mapa.current || !capa.current) return;
    (async () => {
      const L = (await import("leaflet")).default;
      const m = mapa.current!;
      const g = capa.current!;
      g.clearLayers();
      const limites: [number, number][] = [];
      for (const p of puntos) {
        for (const l of lineas) {
          const fin = destino(p.lat, p.lon, l.azimut, l.km);
          L.polyline([[p.lat, p.lon], fin], {
            color: colorCss(l.color), weight: 3, opacity: 0.9, dashArray: l.discontinua ? "6 6" : undefined,
          }).bindTooltip(l.etiqueta, { sticky: true }).addTo(g);
          limites.push(fin);
        }
        const icono = L.divIcon({
          className: "",
          html: `<div class="marcador ${p.clase ?? "n-floja"}">${p.nota !== undefined ? p.nota.toFixed(0) : ""}</div>`,
          iconSize: [30, 30],
          iconAnchor: [15, 15],
        });
        const mk = L.marker([p.lat, p.lon], { icon: icono, title: p.nombre, alt: p.nombre }).addTo(g);
        if (enlazar) {
          mk.bindPopup(
            `<strong>${esc(p.nombre)}</strong>${p.nota !== undefined ? ` · ${p.nota.toFixed(1)}/10` : ""}` +
              `${p.texto ? `<br>${esc(p.texto)}` : ""}<br><a href="/spot/${encodeURIComponent(p.id)}">Ver ficha →</a>`,
          );
        }
        limites.push([p.lat, p.lon]);
      }
      if (ubic) {
        L.circleMarker([ubic.lat, ubic.lon], {
          radius: 7, color: colorCss("var(--superficie)"), weight: 2, fillColor: colorCss("var(--acento)"), fillOpacity: 1,
        }).bindTooltip("Tu ubicación").addTo(g);
      }
      if (zoom && puntos.length === 1 && !lineas.length) m.setView([puntos[0].lat, puntos[0].lon], zoom);
      else if (limites.length) m.fitBounds(L.latLngBounds(limites), { padding: [28, 28], maxZoom: zoom ?? 13 });
      else m.setView([40.8, -3.9], 9);
    })();
  }, [listo, puntos, lineas, ubic, zoom, enlazar, tema]);

  return (
    <div ref={caja} className="mapa-caja" role="region" aria-label={etiqueta} data-listo={listo ? "si" : "no"}>
      {!listo && <div className="mapa-vacio">Cargando mapa…</div>}
    </div>
  );
}
