// iCalendar (RFC 5545) mínimo: eventos con hora (UTC) o de día completo, para calendarios suscribibles.

export interface EventoIcs {
  uid: string;
  titulo: string;
  descripcion?: string;
  lugar?: string;
  geo?: { lat: number; lon: number };
  url?: string;
  /** con hora */
  inicio?: Date;
  fin?: Date;
  /** de día completo: YYYY-MM-DD (fin incluido) */
  dia?: string;
  diaFin?: string;
}

/** Instante UTC de una fecha y hora locales en una zona horaria (sin librerías: con Intl). */
export function utcDesdeLocal(fecha: string, hora: string, zona: string): Date {
  const [h, m] = hora.split(":").map(Number);
  const supuesto = Date.parse(`${fecha}T${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:00Z`);
  const partes = Object.fromEntries(
    new Intl.DateTimeFormat("en-GB", {
      timeZone: zona,
      hourCycle: "h23",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    })
      .formatToParts(new Date(supuesto))
      .map((p) => [p.type, p.value]),
  );
  const visto = Date.parse(`${partes.year}-${partes.month}-${partes.day}T${partes.hour}:${partes.minute}:00Z`);
  return new Date(supuesto - (visto - supuesto));
}

function escapar(t: string): string {
  return t
    .replace(/\\/g, "\\\\")
    .replace(/\n/g, "\\n")
    .replace(/([,;])/g, "\\$1");
}

/** Líneas de más de 75 octetos se parten con CRLF + espacio, sin cortar caracteres UTF-8. */
function plegar(linea: string): string {
  const trozos: string[] = [];
  let actual = "";
  let bytes = 0;
  for (const c of linea) {
    const n = Buffer.byteLength(c);
    if (bytes + n > (trozos.length ? 74 : 75)) {
      trozos.push(actual);
      actual = "";
      bytes = 0;
    }
    actual += c;
    bytes += n;
  }
  trozos.push(actual);
  return trozos.join("\r\n ");
}

const utc = (d: Date) =>
  d
    .toISOString()
    .replace(/[-:]/g, "")
    .replace(/\.\d{3}/, "");
const diaIcs = (f: string) => f.replace(/-/g, "");
function diaSiguiente(f: string): string {
  return new Date(Date.parse(`${f}T00:00:00Z`) + 864e5).toISOString().slice(0, 10);
}

export function calendario(nombre: string, descripcion: string, eventos: EventoIcs[], ahora = new Date()): string {
  const l = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Rasante//Calendario de fotografía//ES",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    `X-WR-CALNAME:${escapar(nombre)}`,
    `X-WR-CALDESC:${escapar(descripcion)}`,
    "X-WR-TIMEZONE:Europe/Madrid",
    // la previsión cambia dos veces al día: que el calendario se refresque a menudo
    "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
    "X-PUBLISHED-TTL:PT6H",
  ];
  for (const e of eventos) {
    l.push("BEGIN:VEVENT", `UID:${e.uid}`, `DTSTAMP:${utc(ahora)}`);
    if (e.inicio) {
      l.push(`DTSTART:${utc(e.inicio)}`, `DTEND:${utc(e.fin ?? new Date(e.inicio.getTime() + 3600e3))}`);
    } else if (e.dia) {
      l.push(`DTSTART;VALUE=DATE:${diaIcs(e.dia)}`, `DTEND;VALUE=DATE:${diaIcs(diaSiguiente(e.diaFin ?? e.dia))}`);
      l.push("TRANSP:TRANSPARENT");
    }
    l.push(`SUMMARY:${escapar(e.titulo)}`);
    if (e.descripcion) l.push(`DESCRIPTION:${escapar(e.descripcion)}`);
    if (e.lugar) l.push(`LOCATION:${escapar(e.lugar)}`);
    if (e.geo) l.push(`GEO:${e.geo.lat.toFixed(5)};${e.geo.lon.toFixed(5)}`);
    if (e.url) l.push(`URL:${e.url}`);
    l.push("END:VEVENT");
  }
  l.push("END:VCALENDAR");
  return l.map(plegar).join("\r\n") + "\r\n";
}
