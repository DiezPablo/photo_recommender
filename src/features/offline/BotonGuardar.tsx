"use client";
// «Guardar para sin conexión»: la ficha (con su GPX, que se genera en el navegador) queda en el dispositivo.
import { useEffect, useState } from "react";
import { estaGuardada, guardar } from "@/features/offline/guardadas";
import { useHidratado } from "@/lib/almacen";

type Estado = "no" | "si" | "guardando" | "error";

export default function BotonGuardar() {
  const hidratado = useHidratado();
  const [estado, setEstado] = useState<Estado>("no");
  const soportado = hidratado && "serviceWorker" in navigator && "caches" in window;

  useEffect(() => {
    if (!soportado) return;
    let vivo = true;
    estaGuardada(location.pathname).then((g) => vivo && g && setEstado("si"));
    return () => {
      vivo = false;
    };
  }, [soportado]);

  if (!soportado) return null;

  async function alternar() {
    const url = location.pathname;
    if (estado === "si") {
      await guardar(url, true);
      setEstado("no");
      return;
    }
    setEstado("guardando");
    setEstado((await guardar(url)) ? "si" : "error");
  }

  return (
    <button type="button" className="enlace-boton" aria-pressed={estado === "si"} onClick={alternar}>
      {estado === "si"
        ? "Guardada sin conexión ✓"
        : estado === "guardando"
          ? "Guardando…"
          : estado === "error"
            ? "No se pudo guardar: reintentar"
            : "Guardar para sin conexión"}
    </button>
  );
}
