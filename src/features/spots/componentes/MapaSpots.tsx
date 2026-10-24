"use client";
// Mapa de spots: los destacados con su nota y, en la portada, el resto como puntos ligeros (canvas). En la
// ficha, un spot con las direcciones del sol, la Vía Láctea y la vista.
import type { LayerGroup } from "leaflet";
import { useEffect, useRef, useState } from "react";
import { useUbicacion } from "@/lib/ubicacion";
import { colorCss, escaparHtml as esc, useMapaBase } from "@/ui/mapa/useMapaBase";

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

// Constante (no `[]` en los parámetros): un array nuevo en cada render volvería a disparar el pintado, que
// mueve el mapa, que vuelve a renderizar… y la página nunca terminaría de navegar.
const SIN_LINEAS: LineaMapa[] = [];

export default function MapaSpots({
  puntos,
  lineas = SIN_LINEAS,
  zoom,
  enlazar = true,
  etiqueta = "Mapa de spots",
  urlTodos,
}: {
  /** con urlTodos, JSON con el resto de spots: se dibujan como puntos ligeros (canvas) */
  urlTodos?: string;
  puntos: PuntoMapa[];
  lineas?: LineaMapa[];
  zoom?: number;
  enlazar?: boolean;
  etiqueta?: string;
}) {
  const { caja, mapa, leaflet, listo, tema, nuevaCapa } = useMapaBase({ scrollWheelZoom: enlazar });
  const ubic = useUbicacion();
  const capa = useRef<LayerGroup | null>(null);
  const [todos, setTodos] = useState<PuntoMapa[]>([]);

  useEffect(() => {
    if (!urlTodos) return;
    fetch(urlTodos)
      .then((r) => (r.ok ? r.json() : []))
      .then(setTodos)
      .catch(() => setTodos([]));
  }, [urlTodos]);

  // Pintar puntos, líneas y ubicación
  useEffect(() => {
    if (!listo || !mapa.current || !leaflet.current) return;
    const L = leaflet.current;
    const m = mapa.current;
    capa.current ??= nuevaCapa();
    const g = capa.current;
    g.clearLayers();
    const limites: [number, number][] = [];
    if (todos.length) {
      // el resto de spots: círculos en canvas (miles de puntos sin ralentizar el móvil)
      const lienzo = L.canvas({ padding: 0.3 });
      const destacados = new Set(puntos.map((p) => p.id));
      for (const p of todos) {
        if (destacados.has(p.id)) continue;
        L.circleMarker([p.lat, p.lon], {
          renderer: lienzo,
          radius: 4,
          weight: 1,
          color: colorCss("var(--superficie)"),
          fillColor: colorCss(`var(--${(p.clase ?? "n-floja").replace("n-", "n-")})`),
          fillOpacity: 0.9,
        })
          .bindPopup(
            `<strong>${esc(p.nombre)}</strong>${p.nota !== undefined ? ` · ${p.nota.toFixed(1)}/10` : ""}` +
              `<br><a href="/spot/${encodeURIComponent(p.id)}">Ver ficha →</a>`,
          )
          .addTo(g);
      }
    }
    for (const p of puntos) {
      for (const l of lineas) {
        const fin = destino(p.lat, p.lon, l.azimut, l.km);
        L.polyline([[p.lat, p.lon], fin], {
          color: colorCss(l.color),
          weight: 3,
          opacity: 0.9,
          dashArray: l.discontinua ? "6 6" : undefined,
        })
          .bindTooltip(l.etiqueta, { sticky: true })
          .addTo(g);
        limites.push(fin);
      }
      // En el mapa general los spots flojos son puntos pequeños: destacan los que merecen la pena
      const pequeno = enlazar && p.nota !== undefined && p.nota < 6.5;
      const lado = pequeno ? 14 : enlazar ? 26 : 30;
      const icono = L.divIcon({
        className: "",
        html: `<div class="marcador ${pequeno ? "pequeno " : ""}${p.clase ?? "n-floja"}" style="width:${lado}px;height:${lado}px">${
          !pequeno && p.nota !== undefined ? p.nota.toFixed(0) : ""
        }</div>`,
        iconSize: [lado, lado],
        iconAnchor: [lado / 2, lado / 2],
      });
      const mk = L.marker([p.lat, p.lon], {
        icon: icono,
        title: p.nombre,
        alt: p.nombre,
        zIndexOffset: Math.round((p.nota ?? 0) * 100),
      }).addTo(g);
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
        radius: 7,
        color: colorCss("var(--superficie)"),
        weight: 2,
        fillColor: colorCss("var(--acento)"),
        fillOpacity: 1,
      })
        .bindTooltip("Tu ubicación")
        .addTo(g);
    }
    if (ubic && enlazar && urlTodos) m.setView([ubic.lat, ubic.lon], 8);
    else if (zoom && puntos.length === 1 && !lineas.length) m.setView([puntos[0].lat, puntos[0].lon], zoom);
    else if (limites.length) {
      // Con Canarias dentro el encuadre se aleja hasta Francia y Marruecos: se encuadra la península
      const peninsula = limites.filter(([la]) => la > 34);
      const encuadre = urlTodos && peninsula.length ? peninsula : limites;
      m.fitBounds(L.latLngBounds(encuadre), { padding: [28, 28], maxZoom: zoom ?? 13 });
    } else m.setView([40.8, -3.9], 9);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listo, puntos, lineas, ubic, zoom, enlazar, tema, todos, urlTodos]);

  return (
    <div ref={caja} className="mapa-caja" role="region" aria-label={etiqueta} data-listo={listo ? "si" : "no"}>
      {!listo && <div className="mapa-vacio">Cargando mapa…</div>}
    </div>
  );
}
