// Panorama del horizonte del terreno (360°) con las direcciones del sol, la luna y la Vía Láctea.
// SVG generado en el servidor: no necesita JavaScript.

export interface MarcaPanorama {
  azimut: number;
  texto: string;
  color: string; // variable CSS
  altura?: number; // grados sobre el horizonte (si se conoce)
}

const ANCHO = 720;
const ALTO = 150;
const MAX_GRADOS = 20; // escala vertical: 0-20° (el relieve rara vez pasa de ahí)
const CARDINALES: [number, string][] = [[0, "N"], [45, "NE"], [90, "E"], [135, "SE"], [180, "S"], [225, "SO"], [270, "O"], [315, "NO"], [360, "N"]];

export default function Panorama({ angulos, marcas }: { angulos: number[]; marcas: MarcaPanorama[] }) {
  const paso = 360 / angulos.length;
  const x = (az: number) => (((az % 360) + 360) % 360) / 360 * ANCHO;
  const y = (g: number) => ALTO - 24 - (Math.max(-2, Math.min(MAX_GRADOS, g)) + 2) / (MAX_GRADOS + 2) * (ALTO - 34);
  const puntos = [...angulos, angulos[0]].map((a, i) => `${(i * paso / 360 * ANCHO).toFixed(1)},${y(a / 10).toFixed(1)}`);
  const relieve = `M0,${ALTO - 24} L${puntos.join(" L")} L${ANCHO},${ALTO - 24} Z`;
  const abierto = angulos.filter((a) => a / 10 < 2).length / angulos.length;
  return (
    <figure className="panorama" style={{ margin: 0 }}>
      <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} role="img"
        aria-label={`Horizonte del terreno: vista abierta en el ${Math.round(abierto * 100)} % de las direcciones`}>
        <line x1="0" x2={ANCHO} y1={y(0)} y2={y(0)} stroke="var(--borde)" strokeDasharray="4 4" />
        <path d={relieve} fill="var(--superficie-2)" stroke="var(--texto-3)" strokeWidth="1.2" />
        {marcas.map((m, i) => (
          <g key={i}>
            <line x1={x(m.azimut)} x2={x(m.azimut)} y1={8} y2={ALTO - 24} stroke={m.color} strokeWidth="2"
              strokeDasharray={m.altura === undefined ? undefined : "3 3"} />
            {m.altura !== undefined && <circle cx={x(m.azimut)} cy={y(m.altura)} r="5" fill={m.color} />}
            <text x={Math.min(ANCHO - 4, Math.max(4, x(m.azimut)))} y={8 + 12 * (i % 3)} fontSize="11"
              textAnchor={x(m.azimut) > ANCHO - 60 ? "end" : x(m.azimut) < 60 ? "start" : "middle"} fill={m.color}>
              {m.texto}
            </text>
          </g>
        ))}
        {CARDINALES.map(([az, t]) => (
          <text key={az} x={Math.min(ANCHO - 8, Math.max(8, x(az === 360 ? 359.9 : az)))} y={ALTO - 8} fontSize="11"
            textAnchor="middle" fill="var(--texto-3)">{t}</text>
        ))}
      </svg>
      <figcaption style={{ fontSize: "0.78rem", color: "var(--texto-3)" }}>
        Relieve calculado con el modelo digital del terreno hasta 60 km (escala vertical 0-{MAX_GRADOS}°, exagerada).
        Vista abierta (relieve &lt; 2°) en el {Math.round(abierto * 100)} % del horizonte.
      </figcaption>
    </figure>
  );
}
