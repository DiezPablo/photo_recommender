"use client";
// Descarga del trazado en GPX, generado en el navegador a partir del trazado de la página.
import { decodificar } from "@/lib/modeloRutas";

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

export default function BotonGpx({ nombre, linea, fichero, atribucion }: { nombre: string; linea: string; fichero: string; atribucion: string }) {
  function descargar() {
    const pts = decodificar(linea).map(([la, lo]) => `<trkpt lat="${la}" lon="${lo}"/>`).join("");
    const gpx = `<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="Rasante" xmlns="http://www.topografix.com/GPX/1/1">` +
      `<metadata><name>${esc(nombre)}</name><copyright author="${esc(atribucion)}"/></metadata>` +
      `<trk><name>${esc(nombre)}</name><trkseg>${pts}</trkseg></trk></gpx>\n`;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([gpx], { type: "application/gpx+xml" }));
    a.download = `${fichero}.gpx`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  return <button type="button" className="enlace-boton" onClick={descargar}>Descargar GPX ↓</button>;
}
