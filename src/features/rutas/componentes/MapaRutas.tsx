"use client";
// Mapa de rutas. Dos modos:
//  - general: un punto por ruta (su inicio) y, al acercarse, los trazados de las celdas a la vista;
//  - una ruta: su trazado con salida y llegada.
import type { LayerGroup } from "leaflet";
import { useEffect, useRef } from "react";
import { celda, type FilaRuta, type TipoRuta, trozos } from "@/features/rutas/modelo";
import { leerUbicacion } from "@/lib/ubicacion";
import { colorCss, escaparHtml, useMapaBase } from "@/ui/mapa/useMapaBase";

/** Desde este zoom se dibujan los trazados del mapa general (antes solo los puntos de salida). */
const ZOOM_TRAZADOS = 10;

const VARIABLE_TIPO: Record<TipoRuta, string> = {
  GR: "--t-gr",
  PR: "--t-pr",
  SL: "--t-sl",
  Europeo: "--t-gr",
  "Camino de Santiago": "--t-santiago",
  "Camino Natural": "--t-natural",
  "Vía Verde": "--t-sl",
  Sendero: "--t-otro",
};

/** Color de cada tipo: rojo GR, amarillo PR, verde SL, como las marcas pintadas del sendero. */
export function colorTipo(t: TipoRuta): string {
  return colorCss(`var(${VARIABLE_TIPO[t] ?? "--t-otro"})`);
}

function popup(f: { id: string; nombre: string; km?: number; subida?: number }) {
  const datos = f.km !== undefined ? `<br>${f.km} km · +${f.subida} m` : "";
  return `<strong>${escaparHtml(f.nombre)}</strong>${datos}<br><a href="/ruta/${encodeURIComponent(f.id)}">Ver ruta →</a>`;
}

type TrazadoCelda = { id: string; nombre: string; tipo: TipoRuta; l: string | string[] };

export default function MapaRutas({
  filas,
  ruta,
  alto,
}: {
  /** modo general: rutas visibles (ya filtradas) */
  filas?: FilaRuta[];
  /** modo una ruta */
  ruta?: { id: string; nombre: string; linea: string | string[]; tipo: TipoRuta };
  alto?: string;
}) {
  const { caja, mapa, leaflet, listo, tema, vista, nuevaCapa } = useMapaBase({ preferCanvas: true });
  const lineas = useRef<LayerGroup | null>(null);
  const puntos = useRef<LayerGroup | null>(null);
  const celdas = useRef(new Map<string, TrazadoCelda[]>());
  const encuadrado = useRef(false);

  // Capas: los trazados debajo de los puntos
  useEffect(() => {
    if (!listo) return;
    lineas.current ??= nuevaCapa();
    puntos.current ??= nuevaCapa();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listo]);

  // Una ruta: trazado, salida y llegada
  useEffect(() => {
    const L = leaflet.current;
    if (!listo || !ruta || !L || !mapa.current || !lineas.current) return;
    const g = lineas.current;
    g.clearLayers();
    const partes = trozos(ruta.linea);
    const pts = partes.flat();
    L.polyline(partes, { color: colorCss("var(--fondo)"), weight: 7, opacity: 0.9 }).addTo(g);
    L.polyline(partes, { color: colorTipo(ruta.tipo), weight: 4 }).addTo(g);
    const marca = (p: [number, number], texto: string, clase: string, titulo: string) =>
      L.marker(p, {
        title: titulo,
        icon: L.divIcon({
          className: "",
          html: `<div class="marca-ruta ${clase}">${texto}</div>`,
          iconSize: [22, 22],
          iconAnchor: [11, 11],
        }),
      }).addTo(g);
    marca(pts[pts.length - 1], "F", "fin", "Llegada");
    marca(pts[0], "S", "salida", "Salida");
    if (!encuadrado.current) {
      mapa.current.fitBounds(L.latLngBounds(pts), { padding: [24, 24] });
      encuadrado.current = true;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listo, ruta, tema]);

  // General: puntos de salida de las rutas filtradas
  useEffect(() => {
    const L = leaflet.current;
    if (!listo || !filas || !L || !mapa.current || !puntos.current) return;
    const g = puntos.current;
    g.clearLayers();
    const borde = colorCss("var(--fondo)");
    for (const f of filas) {
      L.circleMarker([f.lat, f.lon], {
        radius: 4.5,
        weight: 1,
        color: borde,
        fillColor: colorTipo(f.tipo),
        fillOpacity: 0.95,
      })
        .bindPopup(popup(f))
        .addTo(g);
    }
    if (!encuadrado.current && filas.length) {
      const u = leerUbicacion();
      if (u) mapa.current.setView([u.lat, u.lon], 9);
      else {
        // Con Canarias dentro el encuadre se aleja hasta Francia: se encuadra la península
        const peninsula = filas.filter((f) => f.lat > 34);
        const encuadre = (peninsula.length ? peninsula : filas).map((f) => [f.lat, f.lon] as [number, number]);
        mapa.current.fitBounds(L.latLngBounds(encuadre), { padding: [20, 20] });
      }
      encuadrado.current = true;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listo, filas, tema]);

  // General: trazados de las celdas a la vista (y alrededor) cuando hay zoom suficiente
  useEffect(() => {
    const L = leaflet.current;
    const m = mapa.current;
    if (!listo || !filas || !L || !m || !lineas.current) return;
    // hasta que el mapa tiene centro (el encuadre inicial es asíncrono) no hay vista que consultar
    if (!(m as unknown as { _loaded?: boolean })._loaded) return;
    const g = lineas.current;
    if (m.getZoom() < ZOOM_TRAZADOS) {
      g.clearLayers();
      return;
    }
    let cancelado = false;
    (async () => {
      const b = m.getBounds();
      const necesarias: string[] = [];
      for (let la = Math.floor(b.getSouth()) - 1; la <= Math.floor(b.getNorth()); la++)
        for (let lo = Math.floor(b.getWest()) - 1; lo <= Math.floor(b.getEast()); lo++) necesarias.push(`${la}_${lo}`);
      // solo las celdas donde empieza alguna ruta (las demás no existen)
      const conRutas = new Set(filas.map((f) => celda(f.lat, f.lon)));
      await Promise.all(
        necesarias
          .filter((c) => conRutas.has(c) && !celdas.current.has(c))
          .map(async (c) => {
            try {
              const r = await fetch(`/datos-rutas/celda/${c}`);
              celdas.current.set(c, r.ok ? await r.json() : []);
            } catch {
              celdas.current.set(c, []);
            }
          }),
      );
      if (cancelado) return;
      const visibles = new Set(filas.map((f) => f.id));
      g.clearLayers();
      for (const c of necesarias)
        for (const t of celdas.current.get(c) ?? []) {
          if (!visibles.has(t.id)) continue;
          L.polyline(trozos(t.l), { color: colorTipo(t.tipo), weight: 3, opacity: 0.85 })
            .bindPopup(popup(t))
            .addTo(g);
        }
    })();
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listo, filas, vista, tema]);

  return (
    <div
      ref={caja}
      className="mapa-caja"
      style={alto ? { height: alto } : undefined}
      role="region"
      aria-label={ruta ? `Mapa de ${ruta.nombre}` : "Mapa de rutas"}
      data-listo={listo ? "si" : "no"}
    >
      {!listo && <div className="mapa-vacio">Cargando mapa…</div>}
    </div>
  );
}
