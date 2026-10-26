#!/usr/bin/env bash
# Publica los datos generados como ficheros de la release "datos" (se sobrescriben: el historial de git
# no crece con cada previsión) y hace un commit mínimo (public/datos/version.json) para que Vercel
# reconstruya la web, que descarga los datos al compilar (scripts/descargar-datos.mjs).
# Uso: publicar_release.sh "mensaje" fichero1 [fichero2 ...]      (requiere GH_TOKEN con contents:write)
set -euo pipefail
mensaje="$1"; shift
for f in "$@"; do [ -f "$f" ] || { echo "No existe $f: nada que publicar"; exit 0; }; done
# Si ningún fichero ha cambiado no se publica: cada commit de version.json es un despliegue nuevo de Vercel, y
# Vercel guarda los despliegues 30 días (el almacenamiento de despliegues llegaba a 30 GB)
git fetch -q origin main
if python3 - "$@" <<'PY'
import hashlib, json, subprocess, sys
try:
    actual = json.loads(subprocess.run(["git", "show", "origin/main:public/datos/version.json"],
                                       capture_output=True, text=True, check=True).stdout).get("ficheros", {})
except Exception:
    sys.exit(1)
nuevos = {f.split("/")[-1]: hashlib.sha1(open(f, "rb").read()).hexdigest()[:12] for f in sys.argv[1:]}
sys.exit(0 if all(actual.get(k) == v for k, v in nuevos.items()) else 1)
PY
then
  echo "Sin cambios en $*: no se publica (ni se despliega)"
  exit 0
fi
gh release view datos >/dev/null 2>&1 || \
  gh release create datos --title "Datos de previsión" --notes "Ficheros que publica GitHub Actions (se sobrescriben en cada actualización)." --prerelease
gzip -kf9 "$@"
gh release upload datos "$@" $(printf '%s.gz ' "$@") --clobber
echo "Subidos: $*"

tmp=$(mktemp)
python3 - "$tmp" "$@" <<'PY'
import hashlib, json, sys, datetime
salida, ficheros = sys.argv[1], sys.argv[2:]
info = {"actualizado": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "ficheros": {f.split("/")[-1]: hashlib.sha1(open(f, "rb").read()).hexdigest()[:12] for f in ficheros}}
json.dump(info, open(salida, "w"), indent=1)
PY
git config user.name "github-actions"
git config user.email "github-actions@users.noreply.github.com"
for intento in 1 2 3 4 5; do
  git fetch -q origin main
  git reset -q --hard origin/main
  mkdir -p public/datos
  # se conservan las huellas de los ficheros que no se publican ahora (p. ej. spots.geojson en una actualización diaria)
  python3 - "$tmp" public/datos/version.json <<'PY'
import json, sys, os
nuevo = json.load(open(sys.argv[1]))
viejo = json.load(open(sys.argv[2])) if os.path.exists(sys.argv[2]) else {"ficheros": {}}
viejo.get("ficheros", {}).update(nuevo["ficheros"])
json.dump({"actualizado": nuevo["actualizado"], "ficheros": viejo.get("ficheros", {})}, open(sys.argv[2], "w"), indent=1)
PY
  git add public/datos/version.json
  git commit -q -m "$mensaje"
  if git push -q origin HEAD:main; then echo "Publicado: $mensaje"; exit 0; fi
  sleep $((intento * 5))
done
echo "No se pudo publicar tras 5 intentos"; exit 1
