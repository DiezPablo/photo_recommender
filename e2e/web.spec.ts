import { spawn } from "node:child_process";
import { get } from "node:http";
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

/** Código HTTP del servidor local (0 si no responde), sin pasar por el proxy que `fetch` pueda usar. */
function estado(puerto: number): Promise<number> {
  return new Promise((ok) => {
    get({ host: "127.0.0.1", port: puerto, path: "/sin-conexion", timeout: 2000 }, (r) => {
      r.resume();
      ok(r.statusCode ?? 0);
    }).on("error", () => ok(0));
  });
}

/** Espera (sin fallar) a que el mapa tenga teselas, para que las capturas lo muestren. */
async function esperarTeselas(page: Page) {
  await page
    .waitForFunction(() => document.querySelectorAll(".leaflet-tile-loaded").length > 3, null, { timeout: 8000 })
    .catch(() => {});
}

test("los datos publicados responden y son JSON válido sin NaN", async ({ request }) => {
  for (const f of ["/datos/informe.json", "/datos/spots.geojson", "/datos/eventos.json"]) {
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
  await expect(page.locator(".ficha-cab .enlaces").getByRole("link", { name: "Cómo llegar" })).toHaveAttribute(
    "href",
    /google\.com\/maps\/dir/,
  );
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
  // qué se puede ver alrededor a lo largo del año
  await expect(page.locator(".eventos-cerca")).toContainText("Piornos en flor en Guadarrama");
  // aparcamiento, agua y refugios cerca de la salida (si ya se ha publicado la logística)
  if ((await page.request.get("/datos/logistica.json")).ok())
    await expect(page.locator(".logistica")).toContainText("Aparcamiento");
  // a qué hora salir para tener arriba el amanecer y el atardecer
  await expect(page.locator(".plan-luz tbody tr")).toHaveCount(3);
  await expect(page.locator(".plan-luz .hora-salida").first()).toHaveText(/^Sal a las \d\d:\d\d$/);
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

test("calendario: el cielo del mes, eventos de naturaleza y ficha de evento", async ({ page }, info) => {
  const errores = vigilar(page);
  await page.goto("/calendario");
  await expect(page.locator("h1")).toContainText("Qué fotografiar este mes");
  await expect(page.locator(".meses a[aria-current=page]")).toHaveCount(1);
  await expect(page.locator(".lista-cielo li").first()).toBeVisible();
  // otro mes por enlace: octubre trae berrea y otoño
  await page.locator(".meses").getByRole("link", { name: "oct" }).click();
  await expect(page).toHaveURL(/\/calendario\/octubre$/);
  await expect(page.locator(".tarjeta-evento", { hasText: "Berrea" }).first()).toBeVisible();
  // sol y luna llena por los picos del horizonte de los spots
  await expect(page.locator(".alineaciones-mes li").first()).toBeVisible();
  await expect(page.locator(".mapa-caja[data-listo=si]")).toBeVisible();
  await expect(page.locator(".leaflet-overlay-pane path").first()).toBeVisible();
  await esperarTeselas(page);
  await page.screenshot({ path: `${CAPTURAS}/${info.project.name}-calendario.png`, fullPage: true });
  // ficha de un evento: temporada, barra del año, mapa, spots y rutas de la zona
  await page.getByRole("link", { name: "Otoño en la Selva de Irati" }).click();
  await expect(page).toHaveURL(/\/evento\/otono-irati$/);
  await expect(page.locator("h1")).toHaveText("Otoño en la Selva de Irati");
  await expect(page.locator(".temporada")).toContainText(/temporada|Ahora mismo/);
  await expect(page.locator(".barra-anual .pico")).toHaveCount(1);
  await expect(page.locator(".mapa-caja[data-listo=si]")).toBeVisible();
  await expect(page.locator(".lista-cercanos li").first()).toBeVisible();
  await esperarTeselas(page);
  await page.screenshot({ path: `${CAPTURAS}/${info.project.name}-evento.png`, fullPage: true });
  expect(errores).toEqual([]);
});

test("calendario sin JavaScript: meses y eventos son enlaces", async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto("/calendario/abril");
  await expect(page.locator(".tarjeta-evento", { hasText: "Cerezos en flor del Valle del Jerte" })).toBeVisible();
  await page.getByRole("link", { name: "Cerezos en flor del Valle del Jerte" }).click();
  await expect(page).toHaveURL(/\/evento\/cerezo-jerte$/);
  await expect(page.locator(".entradilla")).toBeVisible();
  await ctx.close();
});

test("avisos: zonas para suscribirse y calendario .ics válido", async ({ page, request }) => {
  await page.goto("/alertas");
  await expect(page.locator(".lista-zonas li")).not.toHaveCount(0);
  await expect(page.locator(".lista-zonas a.boton").first()).toHaveAttribute(
    "href",
    /^webcal:\/\/.+\/alertas\/espana\.ics$/,
  );
  const r = await request.get("/alertas/espana.ics");
  expect(r.status()).toBe(200);
  expect(r.headers()["content-type"]).toContain("text/calendar");
  const ics = await r.text();
  expect(ics.startsWith("BEGIN:VCALENDAR\r\n")).toBe(true);
  expect(ics.trimEnd().endsWith("END:VCALENDAR")).toBe(true);
  expect(ics).toContain("BEGIN:VEVENT");
  // ninguna línea pasa de 75 octetos (RFC 5545)
  for (const l of ics.split("\r\n")) expect(new TextEncoder().encode(l).length).toBeLessThanOrEqual(75);
});

test("sin conexión: instalable, ficha guardada y página sin cobertura", async ({ browser, baseURL, request }) => {
  const manifiesto = await (await request.get("/manifest.webmanifest")).json();
  expect(manifiesto.display).toBe("standalone");
  expect((await request.get(manifiesto.icons[0].src)).status()).toBe(200);

  // Para cortar la red de verdad (setOffline no afecta al service worker) esta prueba levanta su propio servidor
  // y lo apaga. Además el service worker exige origen seguro: localhost (fuera del proxy, si lo hay).
  test.skip(!baseURL?.startsWith("http://"), "solo con la build local");
  const puerto = 3190 + test.info().parallelIndex;
  // el binario de next directamente y en su propio grupo de procesos, para poder apagarlo entero
  const servidor = spawn(
    process.execPath,
    ["node_modules/next/dist/bin/next", "start", "-H", "127.0.0.1", "-p", String(puerto)],
    {
      stdio: "ignore",
      detached: true,
    },
  );
  const apagar = () => {
    try {
      process.kill(-servidor.pid!, "SIGKILL");
    } catch {}
  };
  try {
    await expect.poll(() => estado(puerto), { timeout: 30_000 }).toBe(200);
    const proxy = process.env.HTTPS_PROXY;
    const context = await browser.newContext({
      baseURL: `http://localhost:${puerto}`,
      ...(proxy ? { proxy: { server: proxy, bypass: "localhost" } } : {}),
    });
    const page = await context.newPage();

    await page.goto("/rutas");
    await page.getByPlaceholder(/Nombre/).fill("Peñalara");
    await page.locator(".fila-ruta").first().click();
    await expect(page).toHaveURL(/\/ruta\//);
    const ficha = new URL(page.url()).pathname;
    // la primera visita instala el service worker; la página queda controlada al recargar
    await page.evaluate(() => navigator.serviceWorker.ready);
    await page.reload();
    await expect.poll(() => page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
    await page.getByRole("button", { name: "Guardar para sin conexión" }).click();
    await expect(page.getByRole("button", { name: /Guardada sin conexión/ })).toBeVisible();

    apagar();
    await expect.poll(() => estado(puerto)).toBe(0);
    // una página que no se ha visitado: aviso y lista de guardadas
    await page.goto("/calendario/marzo");
    await expect(page.locator("h1")).toHaveText("No hay cobertura");
    await expect(page.locator(".lista-cercanos")).toContainText(/Peñalara/);
    // la guardada se abre sin red, con su GPX
    await page.goto(ficha);
    await expect(page.locator("h1")).toContainText(/Peñalara/i);
    await expect(page.getByRole("button", { name: /Descargar GPX/ })).toBeVisible();
    await context.close();
  } finally {
    apagar();
  }
});

test("planificador de viaje: zona y fechas, días con propuesta y calendario", async ({ page, request }) => {
  const errores = vigilar(page);
  await page.goto("/viaje");
  await page.getByLabel("Zona").selectOption({ label: "Comunidad de Madrid" });
  await page.getByLabel("Días").selectOption("3");
  await page.getByRole("button", { name: "Planificar" }).click();
  await expect(page).toHaveURL(/zona=comunidad-de-madrid/);
  await expect(page.locator(".tarjeta-dia-viaje")).toHaveCount(3);
  await expect(page.locator(".tarjeta-dia-viaje").first().locator(".plan-momento").first()).toBeVisible();
  const ics = page.getByRole("link", { name: /Añadir el plan a tu calendario/ });
  const r = await request.get((await ics.getAttribute("href"))!);
  expect(r.headers()["content-type"]).toContain("text/calendar");
  expect(await r.text()).toContain("BEGIN:VEVENT");
  expect(errores).toEqual([]);
});
