"use client";
// Mapa del viaje: las paradas de cada día, numeradas por día y unidas en orden.
import type { LayerGroup } from "leaflet";
import { useEffect, useRef } from "react";
import type { Parada } from "@/features/viaje/plan";
import { colorCss, escaparHtml as esc, useMapaBase } from "@/ui/mapa/useMapaBase";

const COLOR: Record<Parada["tipo"], string> = {
  amanecer: "var(--n-buena)",
  ruta: "var(--t-gr)",
  atardecer: "var(--n-top)",
  noche: "var(--vl)",
  luna: "var(--luna)",
};
const NOMBRE: Record<Parada["tipo"], string> = {
  amanecer: "Amanecer",
  ruta: "Salida de la ruta",
  atardecer: "Atardecer",
  noche: "Noche",
  luna: "Luna",
};

export default function MapaViaje({ dias }: { dias: { fecha: string; paradas: Parada[] }[] }) {
  const { caja, mapa, leaflet, listo, tema, nuevaCapa } = useMapaBase({ scrollWheelZoom: false });
  const capa = useRef<LayerGroup | null>(null);

  useEffect(() => {
    if (!listo || !mapa.current || !leaflet.current) return;
    const L = leaflet.current;
    capa.current ??= nuevaCapa();
    const g = capa.current;
    g.clearLayers();
    const todos: [number, number][] = [];
    dias.forEach((d, i) => {
      const linea = d.paradas.map((p) => [p.lat, p.lon] as [number, number]);
      if (linea.length > 1)
        L.polyline(linea, { color: colorCss("var(--texto-2)"), weight: 2, opacity: 0.6, dashArray: "4 6" }).addTo(g);
      for (const p of d.paradas) {
        const icono = L.divIcon({
          className: "",
          html: `<div class="parada-viaje" style="background:${colorCss(COLOR[p.tipo])}">${i + 1}</div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });
        L.marker([p.lat, p.lon], { icon: icono, title: `${NOMBRE[p.tipo]}: ${p.nombre}`, alt: p.nombre })
          .bindPopup(`<strong>Día ${i + 1} · ${NOMBRE[p.tipo]}</strong><br>${esc(p.nombre)}`)
          .addTo(g);
        todos.push([p.lat, p.lon]);
      }
    });
    if (todos.length) mapa.current.fitBounds(L.latLngBounds(todos), { padding: [30, 30], maxZoom: 11 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listo, dias, tema]);

  return (
    <div
      ref={caja}
      className="mapa-caja mapa-viaje"
      role="region"
      aria-label="Mapa del viaje"
      data-listo={listo ? "si" : "no"}
    >
      {!listo && <div className="mapa-vacio">Cargando mapa…</div>}
    </div>
  );
}
