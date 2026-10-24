// Perfil de elevación de una ruta (SVG generado en el servidor).
const ANCHO = 720;
const ALTO = 170;
const M = { izq: 44, der: 8, arr: 10, aba: 24 };

function pasoEje(rango: number, objetivo: number): number {
  const bruto = rango / objetivo;
  const p = 10 ** Math.floor(Math.log10(bruto));
  return [1, 2, 5, 10].map((k) => k * p).find((k) => k >= bruto) ?? 10 * p;
}

export default function PerfilRuta({ perfil, nombre }: { perfil: [number, number][]; nombre: string }) {
  if (perfil.length < 2) return null;
  const km = perfil[perfil.length - 1][0] || 1;
  const hs = perfil.map((p) => p[1]);
  const hmin = Math.min(...hs), hmax = Math.max(...hs);
  // escala vertical con al menos 200 m de rango para no exagerar rutas llanas
  const centro = (hmin + hmax) / 2, rango = Math.max(hmax - hmin, 200);
  const lo = centro - rango / 2 - rango * 0.08, hi = centro + rango / 2 + rango * 0.08;
  const x = (d: number) => M.izq + (d / km) * (ANCHO - M.izq - M.der);
  const y = (h: number) => M.arr + (1 - (h - lo) / (hi - lo)) * (ALTO - M.arr - M.aba);
  const linea = perfil.map((p) => `${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join(" L");
  const pasoH = pasoEje(hi - lo, 4), pasoK = pasoEje(km, 6);
  const marcasH = [];
  for (let h = Math.ceil(lo / pasoH) * pasoH; h <= hi; h += pasoH) marcasH.push(h);
  const marcasK = [];
  for (let k = 0; k <= km + 1e-9; k += pasoK) marcasK.push(+k.toFixed(2));
  return (
    <figure className="perfil-ruta">
      <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} role="img"
        aria-label={`Perfil de ${nombre}: de ${hmin} a ${hmax} m de altitud en ${km} km`}>
        {marcasH.map((h) => (
          <g key={h}>
            <line x1={M.izq} x2={ANCHO - M.der} y1={y(h)} y2={y(h)} stroke="var(--borde)" strokeDasharray="2 3" />
            <text x={M.izq - 6} y={y(h) + 3.5} textAnchor="end" fontSize="10" fill="var(--texto-3)">{h}</text>
          </g>
        ))}
        {marcasK.map((k) => (
          <text key={k} x={x(k)} y={ALTO - 8} textAnchor="middle" fontSize="10" fill="var(--texto-3)">{k} km</text>
        ))}
        <path d={`M${x(0)},${ALTO - M.aba} L${linea} L${x(km)},${ALTO - M.aba} Z`} fill="var(--superficie-2)" />
        <path d={`M${linea}`} fill="none" stroke="var(--texto)" strokeWidth="1.6" strokeLinejoin="round" />
      </svg>
      <figcaption>Altitud (m) con el modelo digital del terreno a ~30 m: orientativa.</figcaption>
    </figure>
  );
}
