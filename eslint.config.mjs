// ESLint (configuración plana): reglas de Next.js (core web vitals) y TypeScript.
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const config = [
  ...nextVitals,
  ...nextTs,
  {
    ignores: [
      ".next/**",
      "node_modules/**",
      "public/**",
      "capturas/**",
      "test-results/**",
      "cache/**",
      "next-env.d.ts",
    ],
  },
];

export default config;
