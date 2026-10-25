// Calendario .ics de una zona (/alertas/espana.ics, /alertas/aragon.ics…): estático, se rehace con cada build.
import { calendarioDeZona, zonas } from "@/features/alertas/calendarios";

export const dynamic = "force-static";
export const dynamicParams = false;

export function generateStaticParams() {
  return zonas().map((z) => ({ zona: `${z.slug}.ics` }));
}

export async function GET(_: Request, { params }: { params: Promise<{ zona: string }> }) {
  const nombre = (await params).zona.replace(/\.ics$/, "");
  const zona = zonas().find((z) => z.slug === nombre);
  if (!zona) return new Response("No existe", { status: 404 });
  return new Response(calendarioDeZona(zona), {
    headers: {
      "Content-Type": "text/calendar; charset=utf-8",
      "Content-Disposition": `inline; filename="rasante-${zona.slug}.ics"`,
    },
  });
}
