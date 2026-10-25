"use client";
// Fichas guardadas en este dispositivo. Sin red puede que React no llegue a cargar: entonces las pinta el script
// en línea de /sin-conexion; si carga, las lee este componente.
import Link from "next/link";
import { useEffect, useState } from "react";
import { CACHE_GUARDADAS } from "@/features/offline/guardadas";

async function leer(): Promise<{ url: string; titulo: string }[]> {
  if (!("caches" in window)) return [];
  const c = await caches.open(CACHE_GUARDADAS);
  const lista = [];
  for (const k of await c.keys()) {
    const html = (await (await c.match(k))?.text()) ?? "";
    const titulo = /<title>([^<]*)<\/title>/
      .exec(html)?.[1]
      ?.replace(/ · Rasante$/, "")
      .replace(/&amp;/g, "&");
    lista.push({ url: new URL(k.url).pathname, titulo: titulo ?? k.url });
  }
  return lista;
}

export default function ListaGuardadas() {
  const [lista, setLista] = useState<{ url: string; titulo: string }[] | null>(null);
  useEffect(() => {
    // el script en línea de /sin-conexion solo actúa si React no ha llegado a cargar
    (window as unknown as { __guardadasReact?: boolean }).__guardadasReact = true;
    let vivo = true;
    leer()
      .then((l) => vivo && setLista(l))
      .catch(() => vivo && setLista([]));
    return () => {
      vivo = false;
    };
  }, []);
  return (
    <ul id="guardadas" className="lista-cercanos">
      {lista?.length ? (
        lista.map((g) => (
          <li key={g.url}>
            <Link href={g.url}>{g.titulo}</Link>
          </li>
        ))
      ) : (
        <li>Ninguna todavía. Con conexión, pulsa «Guardar para sin conexión» en la ficha de un spot o de una ruta.</li>
      )}
    </ul>
  );
}
