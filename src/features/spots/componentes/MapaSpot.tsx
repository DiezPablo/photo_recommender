"use client";
import Mapa, { type LineaMapa, type PuntoMapa } from "@/features/spots/componentes/MapaSpots";

export default function MapaSpot({ punto, lineas }: { punto: PuntoMapa; lineas: LineaMapa[] }) {
  return <Mapa puntos={[punto]} lineas={lineas} zoom={12} enlazar={false} etiqueta={`Mapa de ${punto.nombre}`} />;
}
