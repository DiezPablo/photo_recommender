// Descarga los datos publicados por GitHub Actions (release "datos") antes de compilar la web.
// Si no hay red o la release aún no existe, se usan los ficheros que ya haya en public/datos.
import { mkdir, writeFile, stat } from "node:fs/promises";
import { gunzipSync } from "node:zlib";
import path from "node:path";

const REPO = process.env.DATOS_REPO ?? "DiezPablo/photo_recommender";
const FICHEROS = ["informe.json", "spots.geojson", "rutas.json"];
const DIR = path.join(process.cwd(), "public", "datos");

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
      const texto = gunzipSync(Buffer.from(await r.arrayBuffer())).toString("utf8");
      JSON.parse(texto); // que sea JSON válido antes de sustituir nada
      return texto;
    } catch (e) {
      console.warn(`  ${nombre}: intento ${intento} fallido (${e.message})`);
      await new Promise((ok) => setTimeout(ok, 2000 * intento));
    }
  }
  return null;
}

if (process.env.SIN_DESCARGA) {
  console.log("Datos: SIN_DESCARGA, se usan los de public/datos");
} else {
  await mkdir(DIR, { recursive: true });
  for (const f of FICHEROS) {
    const texto = await descargar(f);
    const destino = path.join(DIR, f);
    if (texto) {
      await writeFile(destino, texto);
      console.log(`Datos: ${f} descargado (${(texto.length / 1e6).toFixed(1)} MB)`);
    } else if (await existe(destino)) {
      console.log(`Datos: ${f} no disponible en la release; se usa el local`);
    } else {
      console.warn(`Datos: ${f} no disponible: la web saldrá sin datos`);
    }
  }
}
