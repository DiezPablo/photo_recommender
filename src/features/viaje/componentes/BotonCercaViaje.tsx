"use client";
// «Cerca de mí» en el planificador: rellena la ubicación del formulario y lo envía (sin JS, se elige zona).
import { useState } from "react";
import { pedirUbicacion } from "@/lib/ubicacion";

export default function BotonCercaViaje() {
  const [estado, setEstado] = useState("");
  async function usar(e: React.MouseEvent<HTMLButtonElement>) {
    const form = e.currentTarget.form;
    if (!form) return;
    setEstado("Buscando tu ubicación…");
    const r = await pedirUbicacion();
    if (!r.ok) return setEstado(r.error);
    (form.elements.namedItem("lat") as HTMLInputElement).value = r.ubic.lat.toFixed(3);
    (form.elements.namedItem("lon") as HTMLInputElement).value = r.ubic.lon.toFixed(3);
    form.requestSubmit();
  }
  return (
    <>
      <button type="button" className="boton" onClick={usar}>
        Cerca de mí
      </button>
      {estado && (
        <span role="status" className="estado-ubic">
          {estado}
        </span>
      )}
    </>
  );
}
