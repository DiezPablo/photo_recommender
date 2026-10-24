// Marca pintada del sendero (franja blanca sobre el color de su tipo: rojo GR, amarillo PR, verde SL…).
import { slug, type TipoRuta } from "@/features/rutas/modelo";

export default function MarcaSendero({ tipo }: { tipo: TipoRuta }) {
  return <span className={`marca-sendero t-${slug(tipo)}`} title={tipo} aria-hidden="true" />;
}
