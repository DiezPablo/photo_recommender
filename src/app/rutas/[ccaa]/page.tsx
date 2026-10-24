// Listado completo de las rutas de una comunidad, por provincia (sirve también sin JavaScript).
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import MarcaSendero from "@/features/rutas/componentes/MarcaSendero";
import { cargarRutas, comunidadesRutas, duracion } from "@/features/rutas/datos";

export const dynamicParams = false;

export function generateStaticParams() {
  const c = comunidadesRutas();
  return c.length ? c.map((x) => ({ ccaa: x.slug })) : [{ ccaa: "sin-datos" }];
}

type Props = { params: Promise<{ ccaa: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { ccaa } = await params;
  const c = comunidadesRutas().find((x) => x.slug === ccaa);
  return c ? { title: `Rutas de senderismo en ${c.ccaa}` } : {};
}

export default async function RutasComunidad({ params }: Props) {
  const { ccaa } = await params;
  const c = comunidadesRutas().find((x) => x.slug === ccaa);
  if (!c) notFound();
  const rutas = cargarRutas().rutas.filter((r) => r.ccaa === c.ccaa);
  const provincias = [...new Set(rutas.map((r) => r.provincia))].sort((a, b) => a.localeCompare(b, "es"));
  return (
    <main className="prosa ancha">
      <nav className="migas rotulo" aria-label="Migas">
        <Link href="/rutas">← Rutas</Link>
      </nav>
      <h1>Rutas de senderismo en {c.ccaa}</h1>
      <p className="rotulo">{rutas.length.toLocaleString("es-ES")} rutas</p>
      {provincias.map((p) => (
        <section key={p}>
          <h2>{p}</h2>
          <ol className="lista-rutas">
            {rutas
              .filter((r) => r.provincia === p)
              .sort((a, b) => a.nombre.localeCompare(b.nombre, "es"))
              .map((r) => (
                <li key={r.id}>
                  <Link href={`/ruta/${r.id}`} className="fila-ruta">
                    <MarcaSendero tipo={r.tipo} />
                    <div>
                      <h3>{r.nombre}</h3>
                      <p className="meta">
                        {r.ref && <span>{r.ref}</span>}
                        <span>{r.km.toLocaleString("es-ES")} km</span>
                        <span>+{r.subida} m</span>
                        <span>{duracion(r.horas)}</span>
                        <span>{r.dificultad}</span>
                        {r.circular && <span>circular</span>}
                      </p>
                    </div>
                  </Link>
                </li>
              ))}
          </ol>
        </section>
      ))}
    </main>
  );
}
