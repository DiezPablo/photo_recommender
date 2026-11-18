# 0014 — Funciona sin JavaScript y sin cobertura
Fecha: 2026-10-25 · Estado: vigente
Contexto: en el campo hay mala cobertura; React puede no hidratar.
Decisión: filtros como enlaces o en la URL, formularios GET, tema con script en línea; web instalable con
`public/sw.js` propio (sin librerías) y "Guardar para sin conexión"; avisos como `.ics` estático, sin cuentas.
Consecuencias: las páginas migradas de fauna deben degradar igual; estado del usuario solo en el navegador.
