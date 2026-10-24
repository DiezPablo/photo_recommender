import { expect, type Page, test } from "@playwright/test";

const CAPTURAS = process.env.CAPTURAS ?? "capturas";

/** Falla si hay errores de consola o peticiones que fallen (salvo teselas del mapa, que son externas). */
function vigilar(page: Page) {
  const errores: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error") errores.push(`consola: ${m.text()}`);
  });
  page.on("pageerror", (e) => errores.push(`excepción: ${e.message}`));
  page.on("response", (r) => {
    const u = r.url();
    if (r.status() >= 400 && !u.includes("tile.openstreetmap.org") && !u.includes("upload.wikimedia.org"))
      errores.push(`HTTP ${r.status()} ${u}`);
  });
  return errores;
}

/** Espera (sin fallar) a que el mapa tenga teselas, para que las capturas lo muestren. */
async function esperarTeselas(page: Page) {
  await page
    .waitForFunction(() => document.querySelectorAll(".leaflet-tile-loaded").length > 3, null, { timeout: 8000 })
    .catch(() => {});
}

test("los datos publicados responden y son JSON válido sin NaN", async ({ request }) => {
  for (const f of ["/datos/informe.json", "/datos/spots.geojson"]) {
    const r = await request.get(f);
    expect(r.status(), f).toBe(200);
    const texto = await r.text();
    expect(texto).not.toMatch(/\bNaN\b|Infinity/);
    JSON.parse(texto);
  }
  const fav = await request.get("/favicon.ico");
  expect(fav.status()).toBe(200);
});

test("portada: ranking, mapa con marcadores y filtros", async ({ page }, info) => {
  const errores = vigilar(page);
  const r = await page.goto("/");
  expect(r?.status()).toBe(200);
  const filas = page.locator(".ranking .fila");
  await expect(filas.first()).toBeVisible();
  const n = await filas.count();
  expect(n).toBeGreaterThan(0);

  // notas ordenadas de mayor a menor
  const notas = (await page.locator(".ranking .cifra").allInnerTexts()).map(Number);
  expect([...notas].sort((a, b) => b - a)).toEqual(notas);

  // mapa con un marcador por spot
  await expect(page.locator(".mapa-caja[data-listo=si]")).toBeVisible();
  await expect(page.locator(".leaflet-marker-icon").first()).toBeVisible();
  expect(await page.locator(".leaflet-marker-icon").count()).toBe(n);
  await esperarTeselas(page);
  await page.screenshot({ path: `${CAPTURAS}/${info.project.name}-portada-claro.png`, fullPage: false });

  // filtro de tipo: atardecer
  await page.getByRole("link", { name: "Atardecer" }).first().click();
  await expect(page).toHaveURL(/\/dia\/0\/atardecer$/);
  await expect(page.locator("h1")).toContainText("Atardecer");
  // filtro de día: mañana
  await page
    .locator(".filtros")
    .getByRole("link", { name: /Mañana/ })
    .click();
  await expect(page).toHaveURL(/\/dia\/1\/atardecer$/);
  await expect(page.locator(".ranking .fila").first()).toBeVisible();
  expect(errores).toEqual([]);
});

test("ficha de un spot: notas con desglose, sol, luna, Vía Láctea, fotos y cómo llegar", async ({ page }, info) => {
  const errores = vigilar(page);
  await page.goto("/");
  const primera = page.locator(".ranking .fila").first();
  const nombre = (await primera.locator("h3").innerText()).trim();
  await primera.click();
  await expect(page).toHaveURL(/\/spot\//);
  await expect(page.locator("h1")).toHaveText(nombre);
  const hoy = page.locator("details.dia").first();
  await expect(hoy).toHaveAttribute("open", "");
  await expect(hoy.locator(".nota-tarjeta")).toHaveCount(5);
  await expect(hoy.locator(".desglose li").first()).toBeVisible();
  for (const t of [
    "Salida del sol",
    "Puesta del sol",
    "Hora dorada",
    "Azimut del sol",
    "Noche astronómica",
    "Fase",
    "Núcleo sobre 10°",
    "Contaminación lumínica",
  ])
    await expect(hoy.getByText(t, { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Cómo llegar" })).toHaveAttribute("href", /google\.com\/maps\/dir/);
  await expect(page.locator(".mapa-caja[data-listo=si]")).toBeVisible();
  await expect(page.locator(".leaflet-overlay-pane path").first()).toBeVisible(); // líneas de azimut
  const fotos = page.locator(".galeria figure");
  if (await fotos.count()) await expect(fotos.first().locator("figcaption")).toContainText("©");
  await esperarTeselas(page);
  await page.screenshot({ path: `${CAPTURAS}/${info.project.name}-ficha-claro.png`, fullPage: true });
  expect(errores).toEqual([]);
});

for (const tema of ["oscuro", "noche"] as const) {
  test(`tema ${tema}: se aplica, persiste y no hay errores`, async ({ page }, info) => {
    const errores = vigilar(page);
    await page.goto("/");
    const titulo = tema === "oscuro" ? "Tema oscuro" : "Modo noche (rojo, para el campo)";
    await page.getByRole("button", { name: titulo }).click();
    await expect(page.locator("html")).toHaveAttribute("data-tema", tema);
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-tema", tema);
    await expect(page.locator(".leaflet-marker-icon").first()).toBeVisible();
    const fondo = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    if (tema === "noche") expect(fondo).toBe("rgb(0, 0, 0)");
    await esperarTeselas(page);
    await page.screenshot({ path: `${CAPTURAS}/${info.project.name}-portada-${tema}.png` });
    await page.locator(".ranking .fila").first().click();
    await expect(page.locator("details.dia").first()).toBeVisible();
    await esperarTeselas(page);
    await page.screenshot({ path: `${CAPTURAS}/${info.project.name}-ficha-${tema}.png`, fullPage: true });
    expect(errores).toEqual([]);
  });
}

test("el tema cambia antes de que cargue React (mala cobertura)", async ({ page }) => {
  await page.route("**/_next/static/chunks/**", (r) => r.abort()); // sin la app: solo el script en línea
  await page.goto("/");
  await page.getByRole("button", { name: "Modo noche (rojo, para el campo)" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-tema", "noche");
});

test("funciona sin JavaScript: ranking y filtros son enlaces", async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto("/");
  await expect(page.locator(".ranking .fila").first()).toBeVisible();
  await page.getByRole("link", { name: "Noche" }).first().click();
  await expect(page).toHaveURL(/\/dia\/0\/astro$/);
  await page.locator(".ranking .fila").first().click();
  await expect(page.locator("details.dia").first()).toBeVisible();
  await ctx.close();
});

test("cerca de mí: distancia y filtro por radio", async ({ page, context }) => {
  await context.grantPermissions(["geolocation"]);
  await context.setGeolocation({ latitude: 40.4168, longitude: -3.7038 }); // Madrid, Sol
  await page.goto("/");
  if (await page.evaluate(() => window.isSecureContext)) {
    await page.getByRole("button", { name: "Cerca de mí" }).click();
    // lo que ve el usuario: filtrado a 100 km y dicho en claro
    await expect(page.locator(".resumen-cerca")).toContainText("a menos de 100 km de ti");
    const kms = (await page.locator(".fila .dist").allInnerTexts()).map((t) => parseFloat(t));
    expect(kms.length).toBeGreaterThan(0);
    expect(Math.max(...kms)).toBeLessThanOrEqual(100);
  } else {
    // http://IP no es contexto seguro y el navegador no da la ubicación: la dejamos guardada como haría el botón
    await page.evaluate(() => localStorage.setItem("ubicacion", JSON.stringify({ lat: 40.4168, lon: -3.7038 })));
    await page.reload();
  }
  await expect(page.locator(".fila .dist").first()).toBeVisible();
  const total = await page.locator(".ranking .fila").count();
  await page.getByLabel("Distancia máxima").selectOption("25");
  const cerca = await page
    .locator(".ranking .fila")
    .count()
    .catch(() => 0);
  expect(cerca).toBeLessThanOrEqual(total);
  await page.getByLabel("Ordenar por").selectOption("distancia");
});

test("rutas: buscar, filtrar, ficha con mapa, perfil y GPX", async ({ page }, info) => {
  const errores = vigilar(page);
  await page.goto("/rutas");
  const filas = page.locator(".fila-ruta");
  await expect(filas.first()).toBeVisible();
  await expect(page.locator(".mapa-caja[data-listo=si]")).toBeVisible();
  await esperarTeselas(page);
  await page.screenshot({ path: `${CAPTURAS}/${info.project.name}-rutas.png` });
  const total = await filas.count();
  // filtros: tipo PR y solo circulares reducen la lista
  await page.getByRole("button", { name: "PR", exact: true }).click();
  await page.getByLabel("Solo circulares").check();
  await expect(page.locator(".bloque-ranking h2")).toContainText("rutas");
  expect(await filas.count()).toBeLessThanOrEqual(total);
  // desnivel: todas las rutas de la lista suben entre 600 y 1000 m, y el filtro queda en la URL
  const desnivel = page
    .locator(".campo", { has: page.locator(".rotulo", { hasText: /^Desnivel$/ }) })
    .locator("select");
  await desnivel.selectOption("exigente");
  await expect(page).toHaveURL(/desnivel=exigente/);
  const subidas = await page.locator(".fila-ruta .meta span", { hasText: /^\+\d+ m$/ }).allTextContents();
  expect(subidas.length).toBeGreaterThan(0);
  for (const t of subidas) expect(Number(t.slice(1, -2))).toBeGreaterThanOrEqual(600);
  for (const t of subidas) expect(Number(t.slice(1, -2))).toBeLessThan(1000);
  await desnivel.selectOption("");
  // búsqueda
  await page.getByLabel("Solo circulares").uncheck();
  await page.getByRole("button", { name: "PR", exact: true }).click();
  await page.getByPlaceholder(/Nombre/).fill("Peñalara");
  await expect(filas.first()).toContainText(/Peñalara/i);
  await filas.first().click();
  await expect(page).toHaveURL(/\/ruta\//);
  await expect(page.locator("h1")).toContainText(/Peñalara/i);
  await expect(page.locator(".ficha-datos")).toContainText("km");
  await expect(page.locator(".perfil-ruta svg")).toBeVisible();
  await expect(page.locator(".mapa-caja[data-listo=si]")).toBeVisible();
  await expect(page.locator(".leaflet-overlay-pane path, .leaflet-overlay-pane canvas").first()).toBeVisible();
  const descarga = page.waitForEvent("download");
  await page.getByRole("button", { name: /Descargar GPX/ }).click();
  const d = await descarga;
  expect(d.suggestedFilename()).toMatch(/\.gpx$/);
  await esperarTeselas(page);
  await page.screenshot({ path: `${CAPTURAS}/${info.project.name}-ruta.png`, fullPage: true });
  expect(errores).toEqual([]);
});

test("rutas sin JavaScript: listado por comunidad y ficha", async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto("/rutas");
  await page.locator(".por-comunidad a").first().click();
  await expect(page).toHaveURL(/\/rutas\/[a-z-]+$/);
  await page.locator(".fila-ruta").first().click();
  await expect(page.locator(".perfil-ruta svg")).toBeVisible();
  await ctx.close();
});

test("rutas: los filtros sobreviven a ir a una ruta y volver", async ({ page }) => {
  await page.goto("/rutas");
  await expect(page.locator(".fila-ruta").first()).toBeVisible();
  await page.getByPlaceholder(/Nombre/).fill("Peñalara");
  await expect(page).toHaveURL(/q=Pe%C3%B1alara|q=Peñalara/);
  await page.locator(".fila-ruta").first().click();
  await expect(page).toHaveURL(/\/ruta\//);
  await page.goBack();
  await expect(page.getByPlaceholder(/Nombre/)).toHaveValue("Peñalara");
  await expect(page.locator(".fila-ruta").first()).toContainText(/Peñalara/i);
});
