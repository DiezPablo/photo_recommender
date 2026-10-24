import type { Metadata } from "next";
import Link from "next/link";
import ExploradorRutas from "@/components/ExploradorRutas";
import { cargarRutas, comunidadesRutas } from "@/lib/rutas";

export const metadata: Metadata = {
  title: "Rutas de senderismo",
  description: "Rutas de senderismo de toda España (OpenStreetMap, senderos FEDME y Caminos Naturales) con distancia, desnivel, tiempo y GPX.",
};

export default function PaginaRutas() {
  const { rutas } = cargarRutas();
  const ccaa = comunidadesRutas();
  return (
    <main className="portada rutas">
      <header className="titular">
        <p className="rotulo">{rutas.length.toLocaleString("es-ES")} rutas · OpenStreetMap, FEDME y Caminos Naturales</p>
        <h1>Rutas de senderismo</h1>
      </header>
      <ExploradorRutas comunidades={ccaa.map((c) => c.ccaa)} />
      <nav className="por-comunidad" aria-label="Rutas por comunidad">
        <h2 className="rotulo">Por comunidad</h2>
        <ul>
          {ccaa.map((c) => (
            <li key={c.slug}><Link href={`/rutas/${c.slug}`}>{c.ccaa}</Link> <small>{c.n.toLocaleString("es-ES")}</small></li>
          ))}
        </ul>
      </nav>
    </main>
  );
}
