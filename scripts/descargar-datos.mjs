// Descarga los datos publicados por GitHub Actions (release "datos") antes de compilar la web.
// - Se guardan comprimidos en datos/*.gz, fuera de public/: el servidor los lee con gunzip (src/lib/datos.ts).
//   Así no se publican como estáticos ni pesan sin comprimir en cada función: con todo en public/ cada despliegue
//   ocupaba cientos de MB y Vercel guarda 30 días de despliegues.
// - En public/datos solo va lo que pide el navegador (PUBLICOS) y un resumen para las pruebas.
// Si no hay red o la release aún no existe, se usa lo que ya haya. Con SIN_DESCARGA, los de public/datos.
import { mkdir, readFile, writeFile, stat } from "node:fs/promises";
import { gunzipSync } from "node:zlib";
import path from "node:path";

const REPO = process.env.DATOS_REPO ?? "DiezPablo/photo_recommender";
const FICHEROS = [
  "informe.json",
  "spots.geojson",
  "rutas.json",
  "eventos.json",
  "clima.json",
  "alineaciones.json",
  "logistica.json",
  "verificacion.json",
  "fauna.json",
  "especies.json",
  "dron.json",
  "safaris.json",
  "safaris_recientes.json",
  "safaris_mundo.json",
  "safaris_indice.json",
];
// los únicos que se piden desde el navegador (fetch en ExploradorFauna y ExploradorSafaris)
const PUBLICOS = ["fauna.json", "safaris_indice.json"];
const COMPRIMIDOS = path.join(process.cwd(), "datos");
const PUBLICO = path.join(process.cwd(), "public", "datos");

async function existe(f) {
  try {
    return (await stat(f)).size > 0;
  } catch {
    return false;
  }
}

async function descargar(nombre) {
  const url = `https://github.com/${REPO}/releases/download/datos/${nombre}.gz`;
  for (let intento = 1; intento <= 3; intento++) {
    try {
      const r = await fetch(url, { redirect: "follow" });
      if (r.status === 404) return null;
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const gz = Buffer.from(await r.arrayBuffer());
      JSON.parse(gunzipSync(gz).toString("utf8")); // que sea JSON válido antes de sustituir nada
      return gz;
    } catch (e) {
      console.warn(`  ${nombre}: intento ${intento} fallido (${e.message})`);
      await new Promise((ok) => setTimeout(ok, 2000 * intento));
    }
  }
  return null;
}

/** El JSON de un fichero: del .gz si está, si no del de public/datos (salida local del pipeline). */
async function leer(nombre) {
  const gz = path.join(COMPRIMIDOS, `${nombre}.gz`);
  if (await existe(gz)) return JSON.parse(gunzipSync(await readFile(gz)).toString("utf8"));
  const local = path.join(PUBLICO, nombre);
  return (await existe(local)) ? JSON.parse(await readFile(local, "utf8")) : null;
}

await mkdir(COMPRIMIDOS, { recursive: true });
await mkdir(PUBLICO, { recursive: true });
if (process.env.SIN_DESCARGA) {
  console.log("Datos: SIN_DESCARGA, se usan los de public/datos");
} else {
  for (const f of FICHEROS) {
    const gz = await descargar(f);
    const destino = path.join(COMPRIMIDOS, `${f}.gz`);
    if (gz) {
      await writeFile(destino, gz);
      console.log(`Datos: ${f} descargado (${(gz.length / 1e6).toFixed(1)} MB comprimido)`);
    } else if (await existe(destino)) {
      console.log(`Datos: ${f} no disponible en la release; se usa el local`);
    } else {
      console.warn(`Datos: ${f} no disponible: la web saldrá sin datos`);
    }
  }
  for (const f of PUBLICOS) {
    const gz = path.join(COMPRIMIDOS, `${f}.gz`);
    if (await existe(gz)) await writeFile(path.join(PUBLICO, f), gunzipSync(await readFile(gz)));
  }
}

// Resumen para las pruebas (que también corren contra producción, sin acceso a los ficheros): qué datos hay y un
// spot de costa con mareas.
const disponibles = [];
for (const f of FICHEROS)
  if ((await existe(path.join(COMPRIMIDOS, `${f}.gz`))) || (await existe(path.join(PUBLICO, f)))) disponibles.push(f);
const informe = await leer("informe.json");
const costa = informe?.spots.find((s) => s.dias.some((d) => d.mar && d.mar.mareas.length > 0));
await writeFile(
  path.join(PUBLICO, "resumen.json"),
  JSON.stringify({ ficheros: disponibles, spot_costa: costa?.id ?? null }),
);
