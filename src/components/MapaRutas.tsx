"use client";
// Mapa de rutas (Leaflet, import dinámico). Dos modos:
//  - general: un punto por ruta (su inicio) y, al acercarse, los trazados de las celdas a la vista;
//  - una ruta: su trazado con inicio y final.
import { useEffect, useRef, useState } from "react";
import type { LayerGroup, Map as LMap } from "leaflet";
import { celda, decodificar, type FilaRuta, type TipoRuta } from "@/lib/modeloRutas";
import { leerUbicacion } from "@/lib/ubicacion";

const ZOOM_TRAZADOS = 10;

/** Color de cada tipo (variables CSS: rojo GR, amarillo PR, verde SL, como las marcas del sendero). */
export function colorTipo(t: TipoRuta): string {
  const v = { GR: "--t-gr", PR: "--t-pr", SL: "--t-sl", Europeo: "--t-gr", "Camino de Santiago": "--t-santiago",
    "Camino Natural": "--t-natural", "Vía Verde": "--t-sl", Sendero: "--t-otro" }[t] ?? "--t-otro";
  return getComputedStyle(document.documentElement).getPropertyValue(v).trim() || "#888";
}

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

function popup(f: { id: string; nombre: string; km?: number; subida?: number }) {
  return `<strong>${esc(f.nombre)}</strong>${f.km !== undefined ? `<br>${f.km} km · +${f.subida} m` : ""}` +
    `<br><a href="/ruta/${encodeURIComponent(f.id)}">Ver ruta →</a>`;
}

export default function MapaRutas({ filas, ruta, alto }: {
  /** modo general: rutas visibles (ya filtradas) */
  filas?: FilaRuta[];
  /** modo una ruta */
  ruta?: { id: string; nombre: string; linea: string; tipo: TipoRuta };
  alto?: string;
}) {
  const caja = useRef<HTMLDivElement>(null);
  const mapa = useRef<LMap | null>(null);
  const puntos = useRef<LayerGroup | null>(null);
  const lineas = useRef<LayerGroup | null>(null);
  const celdas = useRef(new Map<string, { id: string; nombre: string; tipo: TipoRuta; l: string }[]>());
  const encuadrado = useRef(false);
  const [listo, setListo] = useState(false);
  const [vista, setVista] = useState(0);
  const [tema, setTema] = useState(0);

  useEffect(() => {
    let cancelado = false;
    (async () => {
      const L = (await import("leaflet")).default;
      await import("leaflet/dist/leaflet.css");
      if (cancelado || !caja.current || mapa.current) return;
      const m = L.map(caja.current, { zoomControl: true, preferCanvas: true });
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(m);
      m.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
      lineas.current = L.layerGroup().addTo(m);
      puntos.current = L.layerGroup().addTo(m);
      m.on("moveend", () => setVista((v) => v + 1));
      mapa.current = m;
      setListo(true);
    })();
    const ft = () => setTema((t) => t + 1);
    window.addEventListener("tema", ft);
    return () => {
      cancelado = true;
      window.removeEventListener("tema", ft);
      mapa.current?.remove();
      mapa.current = null;
    };
  }, []);

  // Una ruta: trazado, inicio y final
  useEffect(() => {
    if (!listo || !ruta || !mapa.current) return;
    (async () => {
      const L = (await import("leaflet")).default;
      const g = lineas.current!;
      g.clearLayers();
      const pts = decodificar(ruta.linea);
      const color = colorTipo(ruta.tipo);
      L.polyline(pts, { color: getComputedStyle(document.documentElement).getPropertyValue("--fondo").trim(), weight: 7, opacity: 0.9 }).addTo(g);
      L.polyline(pts, { color, weight: 4 }).addTo(g);
      const marca = (p: [number, number], texto: string, clase: string) =>
        L.marker(p, { icon: L.divIcon({ className: "", html: `<div class="marca-ruta ${clase}">${texto}</div>`, iconSize: [22, 22], iconAnchor: [11, 11] }), title: texto === "S" ? "Salida" : "Llegada" }).addTo(g);
      marca(pts[pts.length - 1], "F", "fin");
      marca(pts[0], "S", "salida");
      if (!encuadrado.current) {
        mapa.current!.fitBounds(L.latLngBounds(pts), { padding: [24, 24] });
        encuadrado.current = true;
      }
    })();
  }, [listo, ruta, tema]);

  // General: puntos de inicio de las rutas filtradas
  useEffect(() => {
    if (!listo || !filas || !mapa.current) return;
    (async () => {
      const L = (await import("leaflet")).default;
      const g = puntos.current!;
      g.clearLayers();
      const borde = getComputedStyle(document.documentElement).getPropertyValue("--fondo").trim();
      for (const f of filas) {
        L.circleMarker([f.lat, f.lon], { radius: 4.5, weight: 1, color: borde, fillColor: colorTipo(f.tipo), fillOpacity: 0.95 })
          .bindPopup(popup(f)).addTo(g);
      }
      if (!encuadrado.current && filas.length) {
        const u = leerUbicacion();
        if (u) mapa.current!.setView([u.lat, u.lon], 9);
        else {
          const pen = filas.filter((f) => f.lat > 34);
          mapa.current!.fitBounds(L.latLngBounds((pen.length ? pen : filas).map((f) => [f.lat, f.lon] as [number, number])), { padding: [20, 20] });
        }
        encuadrado.current = true;
      }
    })();
  }, [listo, filas, tema]);

  // General: trazados de las celdas a la vista (y alrededor) cuando hay zoom suficiente
  useEffect(() => {
    if (!listo || !filas || !mapa.current) return;
    const m = mapa.current;
    if (m.getZoom() < ZOOM_TRAZADOS) {
      lineas.current?.clearLayers();
      return;
    }
    let cancelado = false;
    (async () => {
      const L = (await import("leaflet")).default;
      const b = m.getBounds();
      const necesarias: string[] = [];
      for (let la = Math.floor(b.getSouth()) - 1; la <= Math.floor(b.getNorth()); la++)
        for (let lo = Math.floor(b.getWest()) - 1; lo <= Math.floor(b.getEast()); lo++) necesarias.push(`${la}_${lo}`);
      // solo las celdas donde empieza alguna ruta (las demás no existen)
      const conRutas = new Set(filas.map((f) => celda(f.lat, f.lon)));
      await Promise.all(necesarias.filter((c) => conRutas.has(c) && !celdas.current.has(c)).map(async (c) => {
        try {
          const r = await fetch(`/datos-rutas/celda/${c}`);
          celdas.current.set(c, r.ok ? await r.json() : []);
        } catch {
          celdas.current.set(c, []);
        }
      }));
      if (cancelado) return;
      const visibles = new Set(filas.map((f) => f.id));
      const g = lineas.current!;
      g.clearLayers();
      for (const c of necesarias)
        for (const t of celdas.current.get(c) ?? []) {
          if (!visibles.has(t.id)) continue;
          L.polyline(decodificar(t.l), { color: colorTipo(t.tipo), weight: 3, opacity: 0.85 }).bindPopup(popup(t)).addTo(g);
        }
    })();
    return () => { cancelado = true; };
  }, [listo, filas, vista, tema]);

  return (
    <div ref={caja} className="mapa-caja" style={alto ? { height: alto } : undefined} role="region"
      aria-label={ruta ? `Mapa de ${ruta.nombre}` : "Mapa de rutas"} data-listo={listo ? "si" : "no"}>
      {!listo && <div className="mapa-vacio">Cargando mapa…</div>}
    </div>
  );
}

