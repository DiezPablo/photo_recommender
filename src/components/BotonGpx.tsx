"use client";
// Descarga del trazado en GPX, generado en el navegador a partir del trazado de la página.
import { trozos } from "@/lib/modeloRutas";

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

export default function BotonGpx({ nombre, linea, fichero, atribucion }: { nombre: string; linea: string | string[]; fichero: string; atribucion: string }) {
  function descargar() {
    // un segmento por trozo: los huecos de la ruta no se unen con una recta
    const segs = trozos(linea).map((t) => `<trkseg>${t.map(([la, lo]) => `<trkpt lat="${la}" lon="${lo}"/>`).join("")}</trkseg>`).join("");
    const gpx = `<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="Rasante" xmlns="http://www.topografix.com/GPX/1/1">` +
      `<metadata><name>${esc(nombre)}</name><copyright author="${esc(atribucion)}"/></metadata>` +
      `<trk><name>${esc(nombre)}</name>${segs}</trk></gpx>\n`;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([gpx], { type: "application/gpx+xml" }));
    a.download = `${fichero}.gpx`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  return <button type="button" className="enlace-boton" onClick={descargar}>Descargar GPX ↓</button>;
}
