# 0001 — Sin backend: Actions calcula, la release `datos` guarda, Vercel sirve
Fecha: 2026-10-23 · Estado: vigente
Contexto: con ~1500 spots el informe pesa ~20 MB y no puede entrar en el historial de git en cada actualización.
Decisión: los JSON generados van a la release `datos` (se sobrescriben con `publicar_release.sh`); solo se hace
commit de `public/datos/version.json`, que dispara el redespliegue, y solo si algún fichero cambió. El prebuild
los descarga comprimidos a `datos/*.gz`, fuera de `public/`; `leerDatos` los lee en el servidor.
Consecuencias: nada de datos generados en git. Cada commit de `version.json` es un despliegue (ver 0002).
