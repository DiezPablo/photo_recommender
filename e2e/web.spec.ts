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

  // «Nubes ahora»: la última imagen del satélite sobre el mapa
  const satelite = page.getByRole("button", { name: "Nubes ahora" });
  await satelite.click();
  await expect(satelite).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".capa-satelite img").first()).toHaveAttribute("src", /view\.eumetsat\.int/);
  await page
    .waitForFunction(
      () =>
        [...document.querySelectorAll<HTMLImageElement>(".capa-satelite img")].some(
          (i) => i.complete && i.naturalWidth > 0,
        ),
      null,
      { timeout: 20_000 },
    )
    .catch(() => {});
  await page.screenshot({ path: `${CAPTURAS}/${info.project.name}-satelite.png`, fullPage: false });
  await satelite.click();
  await expect(page.locator(".capa-satelite")).toHaveCount(0);

  // «Esta temporada» lleva al planificador
  await expect(page.locator(".temporada-portada").getByRole("link", { name: /Planifica un viaje/ })).toHaveAttribute(
    "href",
    "/viaje",
  );

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
  // los spots por los que pasa la ruta (la de la Laguna de Peñalara pasa por la laguna)
  await expect(page.locator("section", { hasText: "Spots en el camino" }).locator("li").first()).toBeVisible();
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
  // paisaje y fauna van separados: la berrea no está en el calendario del paisaje, que enlaza al de fauna
  await expect(page.locator(".tarjeta-evento", { hasText: "Otoño en Ordesa" })).toBeVisible();
  await expect(page.locator(".tarjeta-evento", { hasText: "Berrea" })).toHaveCount(0);
  await expect(page.locator(".aviso-fauna")).toContainText("Fauna en octubre");
  // sol y luna llena por los picos del horizonte de los spots (si ya se han publicado las alineaciones)
  if ((await page.request.get("/datos/alineaciones.json")).ok())
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
    // con su JavaScript ya en caché, sin red React hidrata la página «sin conexión»: la lista debe sobrevivir
    await page.goto("/sin-conexion");
    await page.goto(ficha);

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
  // el mapa con las paradas numeradas por día
  await expect(page.locator(".mapa-viaje[data-listo=si]")).toBeVisible();
  await expect(page.locator(".parada-viaje").first()).toBeVisible();
  await expect(page.locator(".tarjeta-dia-viaje").first().locator(".plan-momento").first()).toBeVisible();
  const ics = page.getByRole("link", { name: /Añadir el plan a tu calendario/ });
  const r = await request.get((await ics.getAttribute("href"))!);
  expect(r.headers()["content-type"]).toContain("text/calendar");
  expect(await r.text()).toContain("BEGIN:VEVENT");
  expect(errores).toEqual([]);
});

test("fauna: buscar por especie, ficha con especies y meses", async ({ page, request }) => {
  test.skip(!(await request.get("/datos/fauna.json")).ok(), "aún no se han publicado los lugares de fauna");
  const errores = vigilar(page);
  await page.goto("/fauna");
  await expect(page.locator("h1")).toHaveText("Dónde ver fauna");
  await expect(page.locator(".lista-fauna li").first()).toBeVisible();
  const total = await page.locator(".lista-fauna li").count();
  await page.getByPlaceholder(/Lugar o especie/).fill("grulla");
  await expect(page).toHaveURL(/q=grulla/);
  await expect(page.locator(".lista-fauna li").first()).toBeVisible();
  expect(await page.locator(".lista-fauna li").count()).toBeLessThanOrEqual(total);
  await page.locator(".lista-fauna li a").first().click();
  await expect(page).toHaveURL(/\/fauna\//);
  await expect(page.locator(".especies li").first()).toBeVisible();
  await expect(page.locator(".meses-fauna > div")).toHaveCount(12);
  await expect(page.locator(".mapa-caja[data-listo=si]")).toBeVisible();
  expect(errores).toEqual([]);
});

test("especies: dónde y cuándo ver el lince, desde el buscador y desde su evento", async ({ page, request }, info) => {
  test.skip(!(await request.get("/datos/especies.json")).ok(), "aún no se han publicado las especies");
  const errores = vigilar(page);
  await page.goto("/fauna");
  await page.getByPlaceholder(/Lugar o especie/).fill("lince");
  await page.locator(".sugerencia-especie a", { hasText: "Lince ibérico" }).click();
  await expect(page).toHaveURL(/\/fauna\/especies\/lince-iberico$/);
  await expect(page.locator("h1")).toHaveText("Lince ibérico");
  await expect(page.locator(".zonas-especie li").first()).toContainText("Jaén");
  await expect(page.locator(".meses-fauna > div")).toHaveCount(12);
  await expect(page.locator(".mapa-caja[data-listo=si]")).toBeVisible();
  await esperarTeselas(page);
  await page.screenshot({ path: `${CAPTURAS}/especie-${info.project.name}.png`, fullPage: true });
  // el celo del lince en el calendario
  await expect(page.locator(".tarjeta-evento", { hasText: "Celo del lince" })).toBeVisible();
  await page.goto("/evento/lince-andujar");
  await expect(page.getByRole("link", { name: "lince ibérico" })).toBeVisible();
  // el catálogo, con las tres pestañas de fauna
  await page.goto("/fauna/especies");
  await expect(page.locator(".pestanas a[aria-current=page]")).toHaveText("Especies");
  expect(await page.locator(".tarjeta-especie").count()).toBeGreaterThanOrEqual(30);
  await page.screenshot({ path: `${CAPTURAS}/especies-${info.project.name}.png` });
  expect(errores).toEqual([]);
});

test("spot de costa: mareas, oleaje y si se puede volar un dron", async ({ page, request }, info) => {
  const informe = await (await request.get("/datos/informe.json")).json();
  const costa = informe.spots.find((s: { dias: { mar?: { mareas: unknown[] } }[] }) =>
    s.dias.some((d) => d.mar && d.mar.mareas.length > 0),
  );
  test.skip(!costa, "el informe publicado aún no trae el mar");
  const errores = vigilar(page);
  await page.goto(`/spot/${costa.id}`);
  await expect(page.locator(".mareas").first()).toContainText("Mareas");
  if ((await request.get("/datos/dron.json")).ok()) {
    await page.locator(".sello-dron").first().click();
    await expect(page).toHaveURL(/#dron$/);
    await expect(page.locator("#dron")).toContainText("ENAIRE");
  }
  await page
    .locator("#dron")
    .screenshot({ path: `${CAPTURAS}/dron-${info.project.name}.png` })
    .catch(() => {});
  expect(errores).toEqual([]);
});

test("safaris: buscar por mes y especie, ficha de parque y especie", async ({ page, request }, info) => {
  test.skip(
    !(await request.get("/datos/safaris.json")).ok() || !(await request.get("/datos/safaris_indice.json")).ok(),
    "aún no se han publicado los safaris",
  );
  const errores = vigilar(page);
  await page.goto("/safaris");
  await expect(page.locator("h1")).toHaveText("Safaris por el mundo");
  await expect(page.locator(".rejilla-safaris li").first()).toBeVisible();
  // en agosto, el Masái Mara (la migración) está en temporada
  await page.getByLabel("Cuándo vas").selectOption("7");
  await page.getByLabel("Continente").selectOption("África");
  const mara = page.locator(".rejilla-safaris li", { hasText: "Masái Mara" });
  await expect(mara).toContainText("Buena época en agosto");
  await page.screenshot({ path: `${CAPTURAS}/safaris-${info.project.name}.png` });
  await mara.getByRole("link").click();
  await expect(page).toHaveURL(/\/safaris\/masai-mara$/);
  await expect(page.locator(".ano-safari")).toBeVisible();
  await expect(page.locator(".visto-ahora")).toBeVisible();
  await expect(page.locator(".mapa-caja[data-listo=si]").first()).toBeVisible();
  await page.screenshot({ path: `${CAPTURAS}/safari-parque-${info.project.name}.png`, fullPage: true });
  // de una especie estrella a su página con los parques donde se ve
  await page.locator(".tarjeta-especie h3 a", { hasText: "León" }).first().click();
  await expect(page).toHaveURL(/\/safaris\/especie\/panthera-leo$/);
  await expect(page.locator(".zonas-especie li").first()).toBeVisible();
  await page.goto("/safaris/guia");
  await expect(page.locator("#operador")).toBeVisible();
  expect(errores).toEqual([]);
});

test("safaris del mundo: ficha de un parque fuera del catálogo con cómo llegar", async ({ page, request }, info) => {
  const r = await request.get("/datos/safaris_indice.json");
  test.skip(!r.ok(), "aún no se ha publicado el índice mundial");
  const { parques } = await r.json();
  const otro = parques.find((p: { d: boolean }) => !p.d);
  const errores = vigilar(page);
  await page.goto(`/safaris/${otro.id}`);
  await expect(page.locator("h1")).toHaveText(otro.n);
  await expect(page.locator("#organiza")).toContainText("Cómo llegar");
  await expect(page.locator("#organiza")).toContainText(/km en línea recta/);
  await expect(page.locator("#empresas")).toContainText("Antes de pagar");
  // los enlaces de reseñas abren la búsqueda de Google Maps centrada en el sitio
  for (const a of await page.locator("#organiza a", { hasText: "Reseñas" }).all())
    expect(await a.getAttribute("href")).toMatch(/^https:\/\/www\.google\.com\/maps\/search\/.+\/@-?\d/);
  // y ninguna web de la lista es un enlace relativo
  for (const a of await page.locator("#organiza a", { hasText: "Web" }).all())
    expect(await a.getAttribute("href")).toMatch(/^https?:\/\//);
  await expect(page.locator(".ano-safari")).toBeVisible();
  await page.screenshot({ path: `${CAPTURAS}/safari-mundo-${info.project.name}.png`, fullPage: true });
  // y el buscador encuentra parques fuera del catálogo
  await page.goto(`/safaris?q=${encodeURIComponent(otro.n.slice(0, 12))}`);
  await expect(page.locator(".rejilla-safaris li").first()).toBeVisible();
  expect(errores).toEqual([]);
});

test("calendario de fauna: eventos de fauna separados del paisaje", async ({ page }) => {
  const errores = vigilar(page);
  await page.goto("/fauna/calendario/octubre");
  await expect(page.locator("h1")).toHaveText("Qué fauna ver en octubre");
  await expect(page.locator(".tarjeta-evento", { hasText: "Berrea" }).first()).toBeVisible();
  await expect(page.locator(".tarjeta-evento", { hasText: "Otoño en Ordesa" })).toHaveCount(0);
  // pestañas entre los dos calendarios, en el mismo mes
  await page.locator(".pestanas").getByRole("link", { name: "Paisaje y cielo" }).click();
  await expect(page).toHaveURL(/\/calendario\/octubre$/);
  // la ficha de un evento de fauna enlaza a su calendario
  await page.goto("/evento/berrea-monfrague");
  await expect(page.locator(".migas")).toContainText("Fauna");
  expect(errores).toEqual([]);
});
