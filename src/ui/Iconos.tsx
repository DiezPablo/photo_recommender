// Iconos SVG en línea (sin librerías): heredan el color del texto.
import type { Filtro } from "@/features/spots/modelo";

type P = { size?: number; titulo?: string };

function Svg({ size = 18, titulo, children }: P & { children: React.ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      role={titulo ? "img" : undefined}
      aria-hidden={titulo ? undefined : true}
      aria-label={titulo}
    >
      {children}
    </svg>
  );
}

export const IconoAmanecer = (p: P) => (
  <Svg {...p}>
    <path d="M12 3v4M5.6 8.6l1.4 1.4M18.4 8.6 17 10M3 16h2M19 16h2M7 16a5 5 0 0 1 10 0M2 20h20M9 5l3-2 3 2" />
  </Svg>
);
export const IconoAtardecer = (p: P) => (
  <Svg {...p}>
    <path d="M12 9V3M5.6 8.6l1.4 1.4M18.4 8.6 17 10M3 16h2M19 16h2M7 16a5 5 0 0 1 10 0M2 20h20M9 6l3 3 3-3" />
  </Svg>
);
export const IconoNoche = (p: P) => (
  <Svg {...p}>
    <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />
    <path d="M17 3v3M15.5 4.5h3" />
  </Svg>
);
export const IconoNiebla = (p: P) => (
  <Svg {...p}>
    <path d="M4 9h12M7 13h13M3 17h11M8 21h10M17 5a3 3 0 0 0-5.6-1.5" />
  </Svg>
);
export const IconoTodo = (p: P) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </Svg>
);
export const IconoSol = IconoTodo;
export const IconoLuna = (p: P) => (
  <Svg {...p}>
    <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />
  </Svg>
);
export const IconoLunaLlena = (p: P) => (
  <Svg {...p}>
    <circle cx="12" cy="10" r="5.5" />
    <path d="M2 20h20M6 17h12" />
  </Svg>
);
export const IconoClaro = (p: P) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="4.5" />
    <path d="M12 2v2M12 20v2M2 12h2M20 12h2" />
  </Svg>
);
export const IconoOscuro = IconoLuna;
export const IconoOjoRojo = (p: P) => (
  <Svg {...p}>
    <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" />
    <circle cx="12" cy="12" r="2.5" fill="currentColor" />
  </Svg>
);
export const IconoUbicacion = (p: P) => (
  <Svg {...p}>
    <path d="M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12Z" />
    <circle cx="12" cy="9" r="2.5" />
  </Svg>
);
export const IconoRuta = (p: P) => (
  <Svg {...p}>
    <path d="M6 19a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM18 9a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z" />
    <path d="M8 17h7a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h7" />
  </Svg>
);
export const IconoCalendario = (p: P) => (
  <Svg {...p}>
    <rect x="4" y="5" width="16" height="15" rx="2" />
    <path d="M4 10h16M9 3v4M15 3v4" />
  </Svg>
);
export const IconoPajaro = (p: P) => (
  <Svg {...p}>
    <path d="M3 13c3 0 5-1 7-4 1.5-2.3 4-3 6-2l3-1-1.5 3c.5 4-2.5 8-7.5 8H6" />
    <path d="M9 17l-2 3M12 17l1 3" />
    <circle cx="16" cy="8.5" r=".6" fill="currentColor" />
  </Svg>
);
export const IconoPrismaticos = (p: P) => (
  <Svg {...p}>
    <circle cx="7" cy="15" r="3.5" />
    <circle cx="17" cy="15" r="3.5" />
    <path d="M10.5 15h3M5 12l1.5-6h3l1 6M19 12l-1.5-6h-3l-1 6" />
  </Svg>
);
export const IconoMochila = (p: P) => (
  <Svg {...p}>
    <path d="M7 8a5 5 0 0 1 10 0v12H7z" />
    <path d="M10 4.5V3h4v1.5M9 13h6v4H9z" />
  </Svg>
);
export const IconoCamara = (p: P) => (
  <Svg {...p}>
    <path d="M4 8h3l2-3h6l2 3h3v11H4z" />
    <circle cx="12" cy="13" r="3.5" />
  </Svg>
);
export const IconoInfo = (p: P) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v6M12 7.5v.5" />
  </Svg>
);
export const IconoFlecha = (p: P) => (
  <Svg {...p}>
    <path d="m9 6 6 6-6 6" />
  </Svg>
);

export function IconoMomento({ momento, size }: { momento: Filtro; size?: number }) {
  switch (momento) {
    case "amanecer":
      return <IconoAmanecer size={size} />;
    case "atardecer":
      return <IconoAtardecer size={size} />;
    case "astro":
      return <IconoNoche size={size} />;
    case "niebla":
      return <IconoNiebla size={size} />;
    case "luna":
      return <IconoLunaLlena size={size} />;
    default:
      return <IconoTodo size={size} />;
  }
}

/** Sol rasante sobre el horizonte. */
export function Logo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 16a7 7 0 0 1 14 0Z" fill="var(--sol)" />
      <path d="M1 16h22M4 19.5h16" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}
